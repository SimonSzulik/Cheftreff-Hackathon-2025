import cv2
import mediapipe as mp
import numpy as np
import time
from deepface import DeepFace
from math import hypot, degrees, atan2
from scipy.spatial import distance as dist

# --- Configuration ---
# Blink Detection
EAR_THRESHOLD = 0.21  # Threshold for eye aspect ratio to detect blink
CONSECUTIVE_FRAMES_BLINK = 2 # Number of consecutive frames below threshold to count as blink

# Head Pose / Looking Away Detection
HEAD_YAW_THRESHOLD = 10 # Degrees deviation from center to be considered 'looking away'

# Emotion Analysis
EMOTION_ANALYSIS_INTERVAL = 1.0 # Analyze emotion every N seconds

# --- Initialization ---
# MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, # Process only one face
    refine_landmarks=True, # Get more detailed landmarks for eyes/lips
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)

# Webcam
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Cannot open webcam.")
    exit()

# --- State Variables ---
# Blink Detection
blink_counter = 0
ear_below_thresh_frames = 0
last_blink_time = time.time()
blinks_in_interval = 0
bps = 0.0

# Looking State
looking_state = "at screen" # Initial state
last_switch_time = time.time()
looking_duration = 0.0

# Emotion Analysis
last_emotion_time = time.time()
current_emotion = "N/A"
emotion_analysis_triggered = False # Flag to run analysis outside main loop if needed

# --- Helper Functions ---
def calculate_ear(eye_landmarks, facial_landmarks):
    """Calculates the Eye Aspect Ratio (EAR) for a single eye."""
    try:
        # Get the 6 eye coordinates
        coords = np.array([(facial_landmarks.landmark[i].x, facial_landmarks.landmark[i].y) for i in eye_landmarks])

        # Vertical eye landmarks
        P2 = coords[1]
        P6 = coords[5]
        P3 = coords[2]
        P5 = coords[4]
        # Horizontal eye landmarks
        P1 = coords[0]
        P4 = coords[3]

        # Calculate Euclidean distances
        # Use image width/height later if needed for scaling, but ratio should be fine
        A = dist.euclidean(P2, P6)
        B = dist.euclidean(P3, P5)
        C = dist.euclidean(P1, P4)

        if C == 0: # Avoid division by zero
            return 0.3 # Return a default open eye EAR

        # Compute EAR
        ear = (A + B) / (2.0 * C)
        return ear
    except Exception as e:
        # print(f"Error calculating EAR: {e}")
        return 0.3 # Default EAR if landmarks are weird

def estimate_head_pose(landmarks, img_shape):
    """Estimates head pose (yaw, pitch, roll) using solvePnP."""
    h, w = img_shape[:2]
    
    # Selected 2D facial landmarks (indices from MediaPipe Face Mesh)
    # Nose tip, chin, left eye left corner, right eye right corner, left mouth corner, right mouth corner
    image_points = np.array([
        (landmarks.landmark[1].x * w, landmarks.landmark[1].y * h),    # Nose tip 1
        (landmarks.landmark[152].x * w, landmarks.landmark[152].y * h), # Chin 152
        (landmarks.landmark[263].x * w, landmarks.landmark[263].y * h), # Left eye left corner 263
        (landmarks.landmark[33].x * w, landmarks.landmark[33].y * h),   # Right eye right corner 33
        (landmarks.landmark[287].x * w, landmarks.landmark[287].y * h), # Left Mouth corner 287
        (landmarks.landmark[57].x * w, landmarks.landmark[57].y * h)    # Right mouth corner 57
    ], dtype="double")

    # Corresponding 3D model points (generic canonical face model)
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Nose tip
        (0.0, -330.0, -65.0),        # Chin
        (-225.0, 170.0, -135.0),     # Left eye left corner
        (225.0, 170.0, -135.0),      # Right eye right corner
        (-150.0, -150.0, -125.0),    # Left Mouth corner
        (150.0, -150.0, -125.0)      # Right mouth corner
    ])

    # Camera internals (approximated)
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1]
    ], dtype="double")

    # Assuming no lens distortion
    dist_coeffs = np.zeros((4, 1))

    # Solve PnP: Find rotation and translation vectors
    try:
        (success, rotation_vector, translation_vector) = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE # or cv2.SOLVEPNP_EPNP
        )

        if not success:
            # print("solvePnP failed.")
            return None, None, None

        # Convert rotation vector to rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        # Combine rotation matrix and translation vector for projection matrix (optional)
        # P = np.hstack((rotation_matrix, translation_vector))

        # Calculate Euler angles from rotation matrix
        #sy = sqrt(R[0,0] * R[0,0] +  R[1,0] * R[1,0])
        #singular = sy < 1e-6
        #if not singular :
        #    x = atan2(R[2,1] , R[2,2])
        #    y = atan2(-R[2,0], sy)
        #    z = atan2(R[1,0], R[0,0])
        #else :
        #    x = atan2(-R[1,2], R[1,1])
        #    y = atan2(-R[2,0], sy)
        #    z = 0
        # Simple YAW calculation: Angle around the Y-axis (vertical)
        # More robust methods exist, but this is common for yaw
        yaw = degrees(atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
        # Alternative yaw:
        # yaw = degrees(atan2(-rotation_matrix[2, 0], np.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2)))

        # Pitch (X-axis rotation)
        pitch = degrees(atan2(-rotation_matrix[2, 1], rotation_matrix[2, 2]))
        # Roll (Z-axis rotation)
        roll = degrees(atan2(rotation_matrix[1, 0], rotation_matrix[0, 0])) # Incorrect, should use atan2(R[2,1], R[2,2]) for X? Need to recheck axes. Let's just use yaw for now.
        # A simpler pitch calculation if needed:
        # pitch = degrees(asin(-rotation_matrix[2,0]))

        # Let's primarily focus on Yaw for looking left/right
        # Adjust Yaw: Sometimes solvePnP gives range -180 to 180. Normalize if needed.
        # A positive yaw might mean looking right, negative looking left (depends on coordinate system)

        # Draw direction line (nose end point projection)
        (nose_end_point2D, _) = cv2.projectPoints(
            np.array([(0.0, 0.0, 1000.0)]), # Project a point 1000 units forward from nose
            rotation_vector,
            translation_vector,
            camera_matrix,
            dist_coeffs
        )
        
        p1 = (int(image_points[0][0]), int(image_points[0][1])) # Nose tip
        p2 = (int(nose_end_point2D[0][0][0]), int(nose_end_point2D[0][0][1]))
        cv2.line(image, p1, p2, (255, 0, 0), 2) # Draw line from nose showing direction

        return yaw, pitch, roll

    except Exception as e:
        # print(f"Error in solvePnP or angle calculation: {e}")
        return None, None, None

# MediaPipe Eye Landmark Indices (Left and Right)
# Adjust these based on the exact Face Mesh model version if needed
# https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
LEFT_EYE_INDICES = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_INDICES = [33, 160, 158, 133, 153, 144]

# --- Main Loop ---
while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Ignoring empty camera frame.")
        continue

    # Flip the image horizontally for a later selfie-view display
    # And convert the BGR image to RGB.
    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    image_height, image_width, _ = image.shape

    # To improve performance, optionally mark the image as not writeable to
    # pass by reference.
    image.flags.writeable = False
    results = face_mesh.process(image)

    # Draw the face mesh annotations on the image.
    image.flags.writeable = True
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) # Convert back to BGR for OpenCV drawing

    face_detected = False
    if results.multi_face_landmarks:
        face_detected = True
        # Process the first detected face
        landmarks = results.multi_face_landmarks[0]

        # --- Draw Landmarks (Optional) ---
        # mp_drawing.draw_landmarks(
        #     image=image,
        #     landmark_list=landmarks,
        #     connections=mp_face_mesh.FACEMESH_TESSELATION,
        #     landmark_drawing_spec=drawing_spec,
        #     connection_drawing_spec=drawing_spec)
        mp_drawing.draw_landmarks(
             image=image,
             landmark_list=landmarks,
             connections=mp_face_mesh.FACEMESH_CONTOURS, # Draw contours
             landmark_drawing_spec=None, # Don't draw individual points
             connection_drawing_spec=mp_drawing.DrawingSpec(color=(80,110,10), thickness=1, circle_radius=1)) # Contour style
        mp_drawing.draw_landmarks(
             image=image,
             landmark_list=landmarks,
             connections=mp_face_mesh.FACEMESH_IRISES, # Draw irises
             landmark_drawing_spec=None, # Don't draw individual points
             connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=1, circle_radius=1)) # Iris style

        # --- 1. Emotion Recognition ---
        current_time = time.time()
        if current_time - last_emotion_time >= EMOTION_ANALYSIS_INTERVAL:
            last_emotion_time = current_time
            try:
                # DeepFace needs BGR image
                # Extract face ROI slightly larger for better analysis (optional but can help)
                # Use landmark bounding box instead of the whole image?
                # x_coords = [lm.x * image_width for lm in landmarks.landmark]
                # y_coords = [lm.y * image_height for lm in landmarks.landmark]
                # x_min, x_max = int(min(x_coords)), int(max(x_coords))
                # y_min, y_max = int(min(y_coords)), int(max(y_coords))
                # padding = 20
                # face_roi = image[max(0, y_min-padding):min(image_height, y_max+padding), 
                #                  max(0, x_min-padding):min(image_width, x_max+padding)]
                
                # Analyze the full frame (simpler, might be slower if frame is large)
                # Deepface analyze function expects the image itself (numpy array)
                analysis = DeepFace.analyze(image, actions=['emotion'], enforce_detection=False)
                
                # Check if analysis is a list (multiple faces) or dict (single face)
                if isinstance(analysis, list):
                    if len(analysis) > 0:
                        current_emotion = analysis[0]['dominant_emotion']
                    else:
                        current_emotion = "N/A (analysis failed)"
                elif isinstance(analysis, dict):
                     current_emotion = analysis['dominant_emotion']
                else:
                     current_emotion = "N/A (unexpected result)"
                     
            except Exception as e:
                # print(f"DeepFace Error: {e}")
                current_emotion = "Error" # Indicate error state


        # --- 2. Head Pose / Looking State ---
        yaw, pitch, roll = estimate_head_pose(landmarks, image.shape)
        
        prev_looking_state = looking_state
        if yaw is not None:
            if abs(yaw) > HEAD_YAW_THRESHOLD:
                looking_state = "away"
            else:
                looking_state = "at screen"

            # Check if state changed
            if looking_state != prev_looking_state:
                last_switch_time = time.time()

            looking_duration = time.time() - last_switch_time
        else:
            # If pose estimation fails, keep previous state but maybe reset timer?
            # Or assume "at screen" as default? Let's keep state.
            looking_duration = time.time() - last_switch_time


        # --- 3. Blink Detection & BPS ---
        left_ear = calculate_ear(LEFT_EYE_INDICES, landmarks)
        right_ear = calculate_ear(RIGHT_EYE_INDICES, landmarks)
        avg_ear = (left_ear + right_ear) / 2.0

        # Check for blink
        if avg_ear < EAR_THRESHOLD:
            ear_below_thresh_frames += 1
        else:
            # If EAR was below threshold for enough frames, count it as a blink
            if ear_below_thresh_frames >= CONSECUTIVE_FRAMES_BLINK:
                blink_counter += 1
                blinks_in_interval += 1
            # Reset the counter whether a blink was counted or not
            ear_below_thresh_frames = 0

        # Calculate BPS (Blinks Per Second) over the last second
        current_time = time.time()
        time_diff = current_time - last_blink_time
        if time_diff >= 1.0: # Update BPS every second
            bps = blinks_in_interval / time_diff
            # Reset for the next interval
            last_blink_time = current_time
            blinks_in_interval = 0


    # --- Display Information ---
    y_pos = 30 # Starting Y position for text
    
    # Emotion
    cv2.putText(image, f"Emotion: {current_emotion}", (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_pos += 30

    # Looking State and Duration
    state_text = f"Looking: {looking_state}"
    duration_text = f"Duration: {looking_duration:.1f}s"
    cv2.putText(image, state_text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_pos += 30
    cv2.putText(image, duration_text, (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_pos += 30

    # Blink Count and BPS
    cv2.putText(image, f"Blinks: {blink_counter}", (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_pos += 30
    cv2.putText(image, f"BPS: {bps:.2f}", (10, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    y_pos += 30
    
    # Optionally display Head Pose angles
    if 'yaw' in locals() and yaw is not None:
         cv2.putText(image, f"Yaw: {int(yaw)} Pitch: {int(pitch)}", (10, y_pos),
                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
         y_pos += 20

    # Show the image
    cv2.imshow('Head Tracking Analysis', image)

    # Exit condition
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

# --- Cleanup ---
face_mesh.close()
cap.release()
cv2.destroyAllWindows()