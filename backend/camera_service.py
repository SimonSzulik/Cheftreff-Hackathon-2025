import cv2
import mediapipe as mp
import numpy as np
import time
import threading
from collections import deque
from deepface import DeepFace
from math import degrees, atan2, sqrt
from scipy.spatial import distance as dist
import traceback # Import traceback for detailed error printing

# --- Default Configuration ---
DEFAULT_CONFIG = {
    # Blink Detection
    "EAR_THRESHOLD": 0.21,
    "CONSECUTIVE_FRAMES_BLINK": 2,
    "BPM_WINDOW_SECONDS": 10.0, # Window to count blinks for extrapolation
    "BPM_UPDATE_INTERVAL": 1.0, # How often to update the smoothed BPM value
    "BPM_SMOOTHING_FACTOR": 0.2, # Alpha for EMA (smaller = smoother, larger = more responsive)

    # Head Pose / Looking Away Detection
    "HEAD_YAW_THRESHOLD": 15,
    "GAZE_RATIO_THRESHOLD_LOW": 0.4,
    "GAZE_RATIO_THRESHOLD_HIGH": 0.55,
    "LOOKING_AWAY_BUFFER_TIME": 1.0,

    # Emotion Analysis
    "EMOTION_ANALYSIS_INTERVAL": 1.0,

    # Camera
    "CAMERA_INDEX": 0,
    "SHOW_VIDEO_FEED": False,
    "DEBUG_LOOKING_STATE": False,
    "DEBUG_POSE_ESTIMATION": False
}

# --- Landmark Indices (Unchanged) ---
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
LEFT_IRIS_CENTER_IDX = 473
RIGHT_IRIS_CENTER_IDX = 468
LEFT_IRIS_INDICES = list(range(473, 478))
RIGHT_IRIS_INDICES = list(range(468, 473))
LEFT_EYE_OUTER_CORNER = 362
LEFT_EYE_INNER_CORNER = 263
RIGHT_EYE_OUTER_CORNER = 33
RIGHT_EYE_INNER_CORNER = 133


class CameraService:
    def __init__(self, config=None):
        self.config = DEFAULT_CONFIG.copy()
        if config: self.config.update(config)

        # MediaPipe Init (Unchanged)
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.mp_drawing = mp.solutions.drawing_utils
        self.drawing_spec_connection = self.mp_drawing.DrawingSpec(thickness=1, color=(100, 150, 100))
        self.drawing_spec_iris = self.mp_drawing.DrawingSpec(thickness=1, circle_radius=1, color=(66, 117, 245))

        # State Variables - Protected by self.lock
        self.current_emotion = "N/A"
        self.confirmed_looking_state = "at screen"
        self.looking_duration = 0.0
        self.smoothed_bpm = 0.0 # <<<--- Renamed from bpm
        self.latest_frame = None

        # Internal state variables
        self._raw_looking_state = "at screen"
        self._last_raw_state_switch_time = time.time()
        self._last_confirmed_state_switch_time = time.time()

        self._blink_counter = 0
        self._ear_below_thresh_frames = 0
        # Use deque for 10-second window for BPM extrapolation
        self.blink_timestamps_10s = deque(maxlen=50) # Maxlen guards against extreme blink rates
        self._last_bpm_update_time = time.time()

        self._last_emotion_time = time.time()
        self._image_height = 480
        self._image_width = 640

        # Threading (Unchanged)
        self.lock = threading.Lock()
        self.thread = None
        self._stop_event = threading.Event()

        print("CameraService Initialized.")
        self._preload_deepface()

    # --- Public Methods (Unchanged Start/Stop/GetFrame) ---
    def start(self):
        if self.thread is not None and self.thread.is_alive(): print("Service already running."); return
        self._stop_event.clear()
        with self.lock: # Reset state variables
             self.confirmed_looking_state = "at screen"; self.looking_duration = 0.0
             self.current_emotion = "N/A"; self.smoothed_bpm = 0.0 # Reset smoothed BPM
             self.blink_timestamps_10s.clear() # Clear deque
             self._raw_looking_state = "at screen"; self._last_raw_state_switch_time = time.time()
             self._last_confirmed_state_switch_time = time.time(); self._last_bpm_update_time = time.time()
             self._last_emotion_time = time.time(); self._blink_counter = 0; self._ear_below_thresh_frames = 0
        self.thread = threading.Thread(target=self._run, daemon=True); self.thread.start()
        print("CameraService started.")

    def stop(self):
        if self.thread is None or not self.thread.is_alive(): print("Service not running."); return
        print("Stopping CameraService..."); self._stop_event.set(); self.thread.join(timeout=5)
        if self.thread.is_alive(): print("Warning: Camera thread did not stop gracefully.")
        self.thread = None; print("CameraService stopped.")

    def get_latest_frame(self):
        with self.lock: frame_copy = self.latest_frame.copy() if self.latest_frame is not None else None
        return frame_copy

    # --- Modified get_current_parameters ---
    def get_current_parameters(self):
        """Returns analysis parameters, including smoothed BPM."""
        with self.lock:
            params = {
                "emotion": self.current_emotion,
                "looking_state": self.confirmed_looking_state,
                "looking_duration": round(self.looking_duration, 1),
                "blinks_per_minute": round(self.smoothed_bpm, 1) # <<<--- Use smoothed_bpm
            }
        return params

    # --- Internal Methods ---
    def _preload_deepface(self): # Unchanged
        try:
             print("Pre-loading DeepFace model...")
             dummy_frame = np.zeros((100, 100, 3), dtype=np.uint8)
             _ = DeepFace.analyze(dummy_frame, actions=['emotion'], enforce_detection=False, silent=True)
             print("DeepFace model loaded.")
        except Exception as e: print(f"Warning: Could not pre-load DeepFace model: {e}")

    def _run(self): # Mostly unchanged, ensures _process_frame(None) on failure
        print("Background thread started.")
        cap = cv2.VideoCapture(self.config["CAMERA_INDEX"])
        if not cap.isOpened(): print(f"Error: Cannot open camera index {self.config['CAMERA_INDEX']}."); return
        while not self._stop_event.is_set():
            success, frame = cap.read()
            if not success: time.sleep(0.1); self._process_frame(None); continue # Pass None on frame read error
            frame_rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
            if self._image_height != frame_rgb.shape[0] or self._image_width != frame_rgb.shape[1]:
                 self._image_height, self._image_width = frame_rgb.shape[:2]
                 print(f"Camera resolution detected: {self._image_width}x{self._image_height}")
            processed_frame_bgr = self._process_frame(frame_rgb)
            if self.config["SHOW_VIDEO_FEED"]:
                with self.lock: self.latest_frame = processed_frame_bgr
            else:
                 with self.lock: self.latest_frame = None
            time.sleep(0.01)
        cap.release()
        if self.config["SHOW_VIDEO_FEED"]: 
            try: cv2.destroyAllWindows(); 
            except: pass
        print("Background thread finished.")


    def _process_frame(self, image_rgb): # Handles processing logic
        current_time = time.time()
        yaw, gaze_ratio_h = None, 0.5 # Initialize defaults

        if image_rgb is None: # Handle no frame case
            face_detected = False; landmarks = None
            image_bgr = np.zeros((self._image_height, self._image_width, 3), dtype=np.uint8)
        else: # Process valid frame
            image_rgb.flags.writeable = False; results = self.face_mesh.process(image_rgb)
            image_rgb.flags.writeable = True; image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            face_detected = bool(results.multi_face_landmarks)
            landmarks = results.multi_face_landmarks[0] if face_detected else None

            if face_detected:
                if self.config["SHOW_VIDEO_FEED"]: self._draw_landmarks(image_bgr, landmarks)
                if current_time - self._last_emotion_time >= self.config["EMOTION_ANALYSIS_INTERVAL"]: self._update_emotion(image_bgr)

                # --- Call Pose Estimation ---
                pose_results = self._estimate_head_pose(landmarks, (self._image_height, self._image_width))
                # Unpack results carefully
                if pose_results: yaw, pitch, roll, p1, p2 = pose_results
                else: yaw, pitch, roll, p1, p2 = None, None, None, None, None

                if self.config["SHOW_VIDEO_FEED"] and p1 and p2: cv2.line(image_bgr, p1, p2, (255, 0, 0), 2)
                gaze_ratio_h = self._calculate_gaze_ratio(landmarks)
                self._update_blinks(landmarks, current_time)

        # --- BPM Calculation (EMA based on 10s window) ---
        if current_time - self._last_bpm_update_time >= self.config["BPM_UPDATE_INTERVAL"]:
             self._update_smoothed_bpm(current_time) # <<<--- Call new function
             self._last_bpm_update_time = current_time

        # --- Update Looking State ---
        self._update_looking_state(yaw, gaze_ratio_h, face_detected, current_time)

        # --- Draw Info Panel ---
        if self.config["SHOW_VIDEO_FEED"]: self._draw_info_panel(image_bgr)

        return image_bgr

    def _update_emotion(self, image_bgr): # Unchanged
        self._last_emotion_time = time.time()
        try:
            analysis = DeepFace.analyze(image_bgr, actions=['emotion'], enforce_detection=False, silent=True)
            emotion = "N/A"
            if isinstance(analysis, list) and len(analysis) > 0: emotion = analysis[0]['dominant_emotion']
            elif isinstance(analysis, dict): emotion = analysis['dominant_emotion']
            with self.lock: self.current_emotion = emotion
        except Exception as e:
             with self.lock: self.current_emotion = "Error"

    # --- Modified Blink Update ---
    def _update_blinks(self, landmarks, current_time):
        """Detects blinks, appends timestamp to 10s deque."""
        left_ear = self._calculate_ear(LEFT_EYE_INDICES, landmarks)
        right_ear = self._calculate_ear(RIGHT_EYE_INDICES, landmarks)
        avg_ear = (left_ear + right_ear) / 2.0

        if avg_ear < self.config["EAR_THRESHOLD"]:
            self._ear_below_thresh_frames += 1
        else:
            if self._ear_below_thresh_frames >= self.config["CONSECUTIVE_FRAMES_BLINK"]:
                with self.lock: self._blink_counter += 1
                self.blink_timestamps_10s.append(current_time) # <<<--- Append to 10s deque
            self._ear_below_thresh_frames = 0

    # --- New Smoothed BPM Calculation ---
    def _update_smoothed_bpm(self, current_time):
         """Calculates smoothed BPM using EMA based on 10s blink window."""
         window_start_time = current_time - self.config["BPM_WINDOW_SECONDS"]

         # Remove timestamps older than the window duration
         while self.blink_timestamps_10s and self.blink_timestamps_10s[0] < window_start_time:
             self.blink_timestamps_10s.popleft()

         # Count blinks in the window
         blinks_in_window = len(self.blink_timestamps_10s)

         # Extrapolate to instantaneous BPM
         instant_bpm = (blinks_in_window / self.config["BPM_WINDOW_SECONDS"]) * 60.0 if self.config["BPM_WINDOW_SECONDS"] > 0 else 0

         # Apply EMA filter
         alpha = self.config["BPM_SMOOTHING_FACTOR"]
         with self.lock:
             # Ensure self.smoothed_bpm exists and is float before calculation
             if not hasattr(self, 'smoothed_bpm') or not isinstance(self.smoothed_bpm, float):
                 self.smoothed_bpm = 0.0 # Initialize if needed
             new_smoothed_bpm = alpha * instant_bpm + (1.0 - alpha) * self.smoothed_bpm
             self.smoothed_bpm = new_smoothed_bpm

    def _update_looking_state(self, yaw, gaze_ratio_h, face_detected, current_time): # Unchanged from previous attempt
        # --- 1. Determine Raw State for This Frame ---
        if face_detected:
            is_raw_away = False
            if yaw is None: is_raw_away = False # Treat pose failure as not away
            else:
                if abs(yaw) > self.config["HEAD_YAW_THRESHOLD"]: is_raw_away = True
                elif not (self.config["GAZE_RATIO_THRESHOLD_LOW"] < gaze_ratio_h < self.config["GAZE_RATIO_THRESHOLD_HIGH"]): is_raw_away = True
            current_raw_state = "away" if is_raw_away else "at screen"
        else: current_raw_state = self._raw_looking_state # Maintain previous raw state if face lost

        if self.config["DEBUG_LOOKING_STATE"]:
             print(f"Time: {current_time:.2f} | Face: {face_detected} | Yaw: {f'{yaw:.1f}' if yaw is not None else 'N/A'} | "
                   f"Gaze: {gaze_ratio_h:.2f} | Raw State: {current_raw_state} | Prev Raw: {self._raw_looking_state} | "
                   f"Confirmed: {self.confirmed_looking_state}")

        # --- 2. Check if Raw State Changed ---
        if current_raw_state != self._raw_looking_state:
             if self.config["DEBUG_LOOKING_STATE"]: print(f"  Raw state changed: {self._raw_looking_state} -> {current_raw_state}")
             self._raw_looking_state = current_raw_state; self._last_raw_state_switch_time = current_time

        # --- 3. Determine New Confirmed State Based on Buffer ---
        new_confirmed_state = self.confirmed_looking_state
        time_in_raw_state = current_time - self._last_raw_state_switch_time
        if self.confirmed_looking_state == "at screen":
            if self._raw_looking_state == "away" and time_in_raw_state >= self.config["LOOKING_AWAY_BUFFER_TIME"]:
                new_confirmed_state = "away"
                if self.config["DEBUG_LOOKING_STATE"]: print(f"  CONFIRMED state changing to AWAY (Raw state '{self._raw_looking_state}' held for {time_in_raw_state:.2f}s >= {self.config['LOOKING_AWAY_BUFFER_TIME']:.2f}s)")
        else: # Confirmed state is "away"
             if self._raw_looking_state == "at screen":
                new_confirmed_state = "at screen"
                if self.config["DEBUG_LOOKING_STATE"]: print(f"  CONFIRMED state changing to AT SCREEN (Raw state is '{self._raw_looking_state}')")

        # --- 4. Apply Changes and Update Duration ---
        if new_confirmed_state != self.confirmed_looking_state:
             with self.lock: self.confirmed_looking_state = new_confirmed_state; self.looking_duration = 0.0
             self._last_confirmed_state_switch_time = current_time
             if self.config["DEBUG_LOOKING_STATE"]: print(f"    State confirmation time: {self._last_confirmed_state_switch_time:.2f}")
        else:
             with self.lock: self.looking_duration = current_time - self._last_confirmed_state_switch_time

    # --- Helper functions ---
    def _draw_landmarks(self, image, landmarks): # Unchanged
        self.mp_drawing.draw_landmarks(image=image, landmark_list=landmarks, connections=self.mp_face_mesh.FACEMESH_CONTOURS, landmark_drawing_spec=None, connection_drawing_spec=self.drawing_spec_connection)
        self.mp_drawing.draw_landmarks(image=image, landmark_list=landmarks, connections=self.mp_face_mesh.FACEMESH_IRISES, landmark_drawing_spec=None, connection_drawing_spec=self.drawing_spec_iris)

    def _draw_info_panel(self, image): # Modified to use smoothed_bpm
        params = self.get_current_parameters()
        y_pos = 30; text_color = (0, 255, 0); font = cv2.FONT_HERSHEY_SIMPLEX; scale = 0.6; thickness = 2
        cv2.putText(image, f"Emotion: {params['emotion']}", (10, y_pos), font, scale, text_color, thickness); y_pos += 25
        cv2.putText(image, f"Looking: {params['looking_state']}", (10, y_pos), font, scale, text_color, thickness); y_pos += 25
        cv2.putText(image, f"Duration: {params['looking_duration']:.1f}s", (10, y_pos), font, scale, text_color, thickness); y_pos += 25
        cv2.putText(image, f"BPM (smooth): {params['blinks_per_minute']:.1f}", (10, y_pos), font, scale, text_color, thickness) # Use smoothed value

    def _calculate_ear(self, eye_landmarks_indices, facial_landmarks): # Unchanged
        try:
            coords_px=np.array([(lm.x*self._image_width,lm.y*self._image_height) for i,lm in enumerate(facial_landmarks.landmark) if i in eye_landmarks_indices]) # More efficient extraction? No, indices are specific.
            coords_px = np.array([(facial_landmarks.landmark[i].x * self._image_width, facial_landmarks.landmark[i].y * self._image_height) for i in eye_landmarks_indices])
            P2, P6 = coords_px[1], coords_px[5]; P3, P5 = coords_px[2], coords_px[4]; P1, P4 = coords_px[0], coords_px[3]
            A = dist.euclidean(P2, P6); B = dist.euclidean(P3, P5); C = dist.euclidean(P1, P4)
            return (A + B) / (2.0 * C) if C > 0 else 0.3
        except: return 0.3

    def _calculate_gaze_ratio(self, facial_landmarks): # Unchanged
        try:
            r_inner = (facial_landmarks.landmark[RIGHT_EYE_INNER_CORNER].x * self._image_width, facial_landmarks.landmark[RIGHT_EYE_INNER_CORNER].y * self._image_height)
            r_outer = (facial_landmarks.landmark[RIGHT_EYE_OUTER_CORNER].x * self._image_width, facial_landmarks.landmark[RIGHT_EYE_OUTER_CORNER].y * self._image_height)
            r_iris = (facial_landmarks.landmark[RIGHT_IRIS_CENTER_IDX].x * self._image_width, facial_landmarks.landmark[RIGHT_IRIS_CENTER_IDX].y * self._image_height)
            r_eye_width = abs(r_inner[0] - r_outer[0]); r_ratio = np.clip((r_iris[0] - r_outer[0]) / r_eye_width if r_eye_width > 0 else 0.5, 0, 1)
            l_inner = (facial_landmarks.landmark[LEFT_EYE_INNER_CORNER].x * self._image_width, facial_landmarks.landmark[LEFT_EYE_INNER_CORNER].y * self._image_height)
            l_outer = (facial_landmarks.landmark[LEFT_EYE_OUTER_CORNER].x * self._image_width, facial_landmarks.landmark[LEFT_EYE_OUTER_CORNER].y * self._image_height)
            l_iris = (facial_landmarks.landmark[LEFT_IRIS_CENTER_IDX].x * self._image_width, facial_landmarks.landmark[LEFT_IRIS_CENTER_IDX].y * self._image_height)
            l_eye_width = abs(l_inner[0] - l_outer[0]); l_ratio = np.clip((l_iris[0] - l_outer[0]) / l_eye_width if l_eye_width > 0 else 0.5, 0, 1)
            return (r_ratio + l_ratio) / 2.0
        except: return 0.5

    # --- Modified Pose Estimation with Aggressive Debugging AND Type Correction ---
    def _estimate_head_pose(self, landmarks, img_shape):
        # --- Print 1: Function Entry ---
        if self.config["DEBUG_POSE_ESTIMATION"]: print("--- Entering _estimate_head_pose ---")

        h, w = img_shape
        p1, p2 = None, None
        try:
            # --- Print 2: Before extracting points ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print("  Extracting image points...")

            # Ensure image points are float32
            image_points = np.array([
                (landmarks.landmark[1].x * w, landmarks.landmark[1].y * h),   # Nose tip
                (landmarks.landmark[152].x * w, landmarks.landmark[152].y * h), # Chin
                (landmarks.landmark[263].x * w, landmarks.landmark[263].y * h), # Left eye left corner
                (landmarks.landmark[33].x * w, landmarks.landmark[33].y * h),   # Right eye right corner
                (landmarks.landmark[287].x * w, landmarks.landmark[287].y * h), # Left Mouth corner
                (landmarks.landmark[57].x * w, landmarks.landmark[57].y * h)    # Right mouth corner
            ], dtype=np.float32) # <<< CHANGED to float32

            if self.config["DEBUG_POSE_ESTIMATION"]: print(f"  Image points (shape {image_points.shape}): {image_points.flatten()}")

            # Ensure model points are float32
            model_points = np.array([
                (0.0, 0.0, 0.0),             # Nose tip
                (0.0, -330.0, -65.0),        # Chin
                (-225.0, 170.0, -135.0),     # Left eye left corner
                (225.0, 170.0, -135.0),      # Right eye right corner
                (-150.0, -150.0, -125.0),    # Left Mouth corner
                (150.0, -150.0, -125.0)      # Right mouth corner
            ], dtype=np.float32) # <<< CHANGED to float32

            # Ensure camera matrix is float32 (Corrected definition slightly)
            focal_length = float(w) # Use float for calculations
            center = (float(w / 2), float(h / 2))
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype=np.float32) # <<< CHANGED to float32

            # Ensure distortion coefficients are float32
            dist_coeffs = np.zeros((4, 1), dtype=np.float32) # <<< CHANGED to float32

            # --- Print 3: Before solvePnP ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print("  Calling solvePnP (EPNP)...")
            # Ensure inputs have the correct number of points before calling
            if len(image_points) >= 4 and len(image_points) == len(model_points):
                success, rotation_vector, translation_vector = cv2.solvePnP(
                    model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_EPNP)
            else:
                if self.config["DEBUG_POSE_ESTIMATION"]:
                     print(f"  Skipping solvePnP: Insufficient points ({len(image_points)}) or mismatch with model points ({len(model_points)}).")
                success = False # Mark as failure if not enough points

            # --- Print 4: After solvePnP ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print(f"  solvePnP result: success={success}")

            if not success:
                # --- Print 5: Before returning None due to success=False ---
                if self.config["DEBUG_POSE_ESTIMATION"]: print("  Returning None because solvePnP failed or was skipped.")
                return None # Return None tuple directly

            # --- Print 6: Before calculating angles ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print("  Calculating angles...")
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            sy = sqrt(rotation_matrix[0,0]**2 + rotation_matrix[1,0]**2); singular = sy < 1e-6
            if not singular:
                pitch = degrees(atan2(rotation_matrix[2,1], rotation_matrix[2,2])); yaw = degrees(atan2(-rotation_matrix[2,0], sy)); roll = degrees(atan2(rotation_matrix[1,0], rotation_matrix[0,0]))
            else:
                pitch = degrees(atan2(-rotation_matrix[1,2], rotation_matrix[1,1])); yaw = degrees(atan2(-rotation_matrix[2,0], sy)); roll = 0
            if self.config["DEBUG_POSE_ESTIMATION"]: print(f"  Calculated Angles: Yaw={yaw:.1f}, Pitch={pitch:.1f}, Roll={roll:.1f}")


            if self.config["SHOW_VIDEO_FEED"]:
                if self.config["DEBUG_POSE_ESTIMATION"]: print("  Calculating projection points...")
                # Project points needs compatible types too
                (nose_end_point2D, _) = cv2.projectPoints(np.array([(0.0, 0.0, 500.0)], dtype=np.float32), # Ensure input point is float32
                                                            rotation_vector.astype(np.float32),  # Ensure vectors are float32
                                                            translation_vector.astype(np.float32),# Ensure vectors are float32
                                                            camera_matrix, # Already float32
                                                            dist_coeffs)  # Already float32
                # Ensure image_points[0] exists before accessing
                if image_points is not None and len(image_points) > 0:
                     p1 = (int(image_points[0][0]), int(image_points[0][1]))
                     p2 = (int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
                     if self.config["DEBUG_POSE_ESTIMATION"]: print(f"  Projection points: p1={p1}, p2={p2}")
                else:
                     if self.config["DEBUG_POSE_ESTIMATION"]: print("  Cannot calculate projection points: image_points is empty.")


            # --- Print 7: Before returning valid results ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print(f"  Returning valid pose: Yaw={yaw:.1f}")
            return yaw, pitch, roll, p1, p2

        except Exception as e:
            # --- Print 8: Exception occurred ---
            print(f"!!! EXCEPTION in _estimate_head_pose: {e} !!!")
            traceback.print_exc() # Print detailed traceback
            # --- Print 9: Before returning None due to exception ---
            if self.config["DEBUG_POSE_ESTIMATION"]: print("  Returning None because of exception.")
            return None # Return None tuple on any exception

# --- Example Usage ---
if __name__ == "__main__":
    print("Starting Camera Service Example...")
    service_config = {
        "SHOW_VIDEO_FEED": True,
        "DEBUG_LOOKING_STATE": False, # Keep looking state debug ON
        "DEBUG_POSE_ESTIMATION": False # Keep pose debug ON
    }
    service = CameraService(config=service_config)
    service.start()
    last_print_time = time.time()
    try:
        while True:
            current_time = time.time()
            if current_time - last_print_time >= 2.0:
                params = service.get_current_parameters(); print(f"[{time.strftime('%H:%M:%S')}] Params: {params}"); last_print_time = current_time
            frame = service.get_latest_frame()
            if frame is not None: cv2.imshow("Camera Service Feed", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'): break
            if not service.thread or not service.thread.is_alive(): print("Service thread stopped."); break
    except KeyboardInterrupt: print("KeyboardInterrupt received.")
    finally:
        print("Stopping service..."); service.stop(); 
    try: 
        cv2.destroyAllWindows(); 
    except: 
        pass; 
        print("Example finished.")



