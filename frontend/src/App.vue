<template>
  <v-app theme="dark" id="app-root">
    <v-main class="fill-height">
      <v-container fluid class="fill-height pa-0">
        <v-row class="fill-height no-gutters">
          <v-col cols="4" class="fill-height border-right">
            <v-toolbar flat color="#2e3c43" density="compact">
              <v-toolbar-title>Mentors</v-toolbar-title>
              <v-spacer></v-spacer>
            </v-toolbar>
            <v-text-field
              v-model="searchTerm"
              density="compact"
              variant="solo-filled"
              label="Search or start new chat"
              append-inner-icon="mdi-magnify"
              single-line
              hide-details
              flat
              class="px-4 py-2"
              bg-color="#2e3c42" ></v-text-field>
            <v-list lines="two" class="mentor-list overflow-y-auto">
              <v-list-item
                v-for="mentor in filteredMentors"
                :key="mentor.id"
                @click="selectMentor(mentor)"
                :active="selectedMentor && selectedMentor.id === mentor.id"
                active-color="primary"
                class="mentor-item py-3"
              >
                <template v-slot:prepend>
                  <v-avatar size="40">
                    <v-img :src="mentor.avatar" :alt="mentor.name"></v-img>
                  </v-avatar>
                </template>
                <v-list-item-content>
                  <v-list-item-title class="font-weight-medium">{{ mentor.name }}</v-list-item-title>
                  <v-list-item-subtitle class="text-caption">{{ mentor.lastMessage }}</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </v-list>
          </v-col>

          <v-col cols="8" class="d-flex flex-column fill-height chat-window">
            <div v-if="selectedMentor" class="d-flex flex-column fill-height">
              <v-toolbar flat color="#2e3c43" density="compact">
                <template v-slot:prepend>
                   <v-avatar size="36">
                     <v-img :src="selectedMentor.avatar" :alt="selectedMentor.name"></v-img>
                   </v-avatar>
                </template>
                <v-toolbar-title>{{ selectedMentor.name }}</v-toolbar-title>
                <v-spacer></v-spacer> 
              </v-toolbar>
              <v-divider></v-divider>

              <v-container ref="chatContainer" class="flex-grow-1 overflow-y-auto chat-messages-container pa-4">
                <div v-for="message in messages" :key="message.id"
                     :class="{'message-sent': message.sender === 'me', 'message-received': message.sender === 'mentor'}"
                     class="d-flex"
                >
                  <v-chip
                    variant="flat"
                    :color="message.sender === 'me' ? 'green' : 'primary'"
                    rounded="lg"
                    class="message-bubble my-1 px-3 py-2"
                  >
                    {{ message.text }}
                  </v-chip>
                </div>
              </v-container>

              <div class="message-input-area pa-3"> <v-text-field
                  v-model="newMessage"
                  density="compact"
                  variant="solo"
                  flat
                  hide-details
                  placeholder="Type a message"
                  class="message-input mr-3"
                  bg-color="#2a3942"
                  rounded="xl"
                  @keyup.enter="sendMessage"
                ></v-text-field>
                <v-btn
                  color="#00a884"
                  @click="sendMessage"
                  size="large"
                  rounded="circle"
                  class="send-button"
                  :disabled="!newMessage.trim()"
                >
                  <v-icon>mdi-send</v-icon>
                </v-btn>
              </div>
            </div>
            <div v-else class="d-flex align-center justify-center fill-height no-mentor-selected">
              <v-icon size="64" color="#8696a0">mdi-message-text-outline</v-icon>
              <v-subheader style="color: #8696a0;" class="text-h6">Select a mentor to start chatting</v-subheader>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue';

const BACKEND_URL = 'http://localhost:8000';

const mentors = ref([
  { id: 'marieBelle', name: 'Marie-Belle', avatar: '/profile_pictures/mary_belle.png', lastMessage: 'Math' },
  { id: 'vanClaude', name: 'Van Claude', avatar: '/profile_pictures/van_claude.png', lastMessage: 'French' },
  { id: 'sophiaLane', name: 'Sophia Lane', avatar: '/profile_pictures/sophia_lane.png', lastMessage: 'English' },
  { id: 'maximilianKoehler', name: 'Maximilian Koehler', avatar: '/profile_pictures/maximilian_koehler.png', lastMessage: 'German' },
  { id: 'eliseSchmitz', name: 'Elise Schmitz', avatar: '/profile_pictures/elise_schmitz.png', lastMessage: 'Biology' },
  { id: 'isabellaReyes', name: 'Isabella Reyes', avatar: '/profile_pictures/isabella_reyes.png', lastMessage: 'Music' },
  { id: 'danielHartmann', name: 'Daniel Hartmann', avatar: '/profile_pictures/daniel_hartmann.png', lastMessage: 'Geography' },
  { id: 'lenaFischer', name: 'Lena Fischer', avatar: '/profile_pictures/lena_fischer.png', lastMessage: 'Physics' },
  { id: 'amiraSolis', name: 'Amira Solis', avatar: '/profile_pictures/amira_solis.png', lastMessage: 'Chemistry' },
  { id: 'liamReyes', name: 'Liam Reyes', avatar: '/profile_pictures/liam_reyes.png', lastMessage: 'Computer Science' },
  { id: 'annaLuciaBaumann', name: 'Anna Lucia Baumann', avatar: '/profile_pictures/anna-lucia_baumann.png', lastMessage: 'Religion' },
  { id: 'jordanKeller', name: 'Jordan Keller', avatar: '/profile_pictures/jordan_keller.png', lastMessage: 'Sports' },
  { id: 'oliviaSchmidt', name: 'Olivia Schmidt', avatar: '/profile_pictures/olivia_schmidt.png', lastMessage: 'Psychology' },
  { id: 'maxWeber', name: 'Max Weber', avatar: '/profile_pictures/max_weber.png', lastMessage: 'Economics' },
  { id: 'liamFischer', name: 'Liam Fischer', avatar: '/profile_pictures/liam_fischer.png', lastMessage: 'Politics' }
]);


const searchTerm = ref('');

import { computed } from 'vue';

const filteredMentors = computed(() =>
  mentors.value.filter(mentor =>
    mentor.name.toLowerCase().includes(searchTerm.value.toLowerCase()) ||
    mentor.lastMessage.toLowerCase().includes(searchTerm.value.toLowerCase())
  )
);

const selectedMentor = ref(null);
const messages = ref([]);
const newMessage = ref('');
let nextMessageId = 1;

const chatContainer = ref(null);

const selectMentor = async (mentor) => {
  selectedMentor.value = mentor;

  const response = await fetch(`${BACKEND_URL}/history/${mentor.id}`);
  const data = await response.json();

  messages.value = data.messages || [];
  nextMessageId = messages.value.length;

  await nextTick();
  scrollToBottom();
};

const sendMessage = async () => {
  if (newMessage.value.trim() !== '' && selectedMentor.value) {
    const userText = newMessage.value.trim();

    messages.value.push({ id: nextMessageId++, sender: 'me', text: userText });
    newMessage.value = '';

    await nextTick();
    scrollToBottom();

    // Send to backend
    const res = await fetch(`${BACKEND_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tutor_id: selectedMentor.value.id,
        message: userText
      })
    });

    const data = await res.json();
    messages.value.push({ id: nextMessageId++, sender: 'mentor', text: data.reply });

    await nextTick();
    scrollToBottom();
  }
};

const scrollToBottom = () => {
  if (chatContainer.value) {
    const element = chatContainer.value.$el;
    element.scrollTop = element.scrollHeight;
  }
};

watch(messages, () => {
    nextTick(() => {
        scrollToBottom();
    });
}, { deep: true });
onMounted(() => {
  setInterval(async () => {
    if (selectedMentor.value) {
      const response = await fetch(`${BACKEND_URL}/tracking/${selectedMentor.value.id}`);
      const data = await response.json();
    
    if (data.reply === 'motivate') {
      const res = await fetch(`${BACKEND_URL}/motivate/${selectedMentor.value.id}`);
      const data = await res.json();
      messages.value.push({ id: nextMessageId++, sender: 'mentor', text: data.reply });
    }

    await nextTick();
    scrollToBottom();
    }
  }, 5000); // every 5 seconds
});
</script>

<style scoped>
#app-root {
  background-color: #111b21;
  height: 100vh;
}

.border-right {
  border-right: 1px solid #2a3942;
}

.send-button {
  width: 48px !important;
  height: 48px !important;
  min-width: 48px !important;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mentor-list {
  background-color: #1f2c34;
  /* Calculate height considering toolbar (48px) and search (approx 60px including padding) */
  height: calc(100% - 48px - 60px);
}

.mentor-item {
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.mentor-item:hover {
  background-color: #2a3942;
}

.v-list-item--active.mentor-item {
    background-color: #2a3942 !important;
}


.chat-window {
    background-color: #111b21;
}

.chat-messages-container {
  flex-grow: 1;
  overflow-y: auto;
  /* Removed padding-bottom that accounted for v-footer */
  padding: 16px; /* Adjusted padding */
}

.chat-messages-container::-webkit-scrollbar {
  width: 8px;
}

.chat-messages-container::-webkit-scrollbar-track {
  background: #1f2c34;
}

.chat-messages-container::-webkit-scrollbar-thumb {
  background: #50606a;
  border-radius: 4px;
}

.chat-messages-container::-webkit-scrollbar-thumb:hover {
  background: #60707a;
}

.message-sent,
.message-received {
  display: flex;
}

.message-sent {
  justify-content: flex-end;
}

.message-received {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: 0 1px 0.5px rgba(0, 0, 0, 0.13);
  height: auto;
}

/* Style for the new input area div */
.message-input-area {
    background-color: #2a3942; /* Background color */
    display: flex; /* Use flexbox to align text field and button */
    align-items: center; /* Vertically center content */
    padding: 12px 16px; /* Adjusted padding */
    flex-shrink: 0; /* Prevent it from shrinking */
}

.message-input {
    flex-grow: 1; /* Allow text field to take available space */
}

.message-input .v-input__control {
    border-radius: 24px;
    overflow: hidden;
}

.message-input .v-field__input {
    padding-top: 8px !important;
    padding-bottom: 8px !important;
    min-height: unset !important;
}

.no-mentor-selected {
    flex-direction: column;
    gap: 16px;
}
</style>