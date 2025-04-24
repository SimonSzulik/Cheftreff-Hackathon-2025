<template>
  <v-app :class="{'strobe': isStrobing}" theme="dark" id="app-root">
    <v-main class="fill-height">
      <v-container fluid class="fill-height">
        <v-row class="fill-height">
          <v-col cols="4" style="background-color: #232d36;" class="fill-height">
            <v-toolbar flat dark>
              <v-toolbar-title>Mentors</v-toolbar-title>
              <v-spacer></v-spacer>
              <v-btn icon>
                <v-icon>mdi-message-plus-outline</v-icon>
              </v-btn>
              <v-btn icon>
                <v-icon>mdi-dots-vertical</v-icon>
              </v-btn>
            </v-toolbar>
            <v-list rounded dark class="fill-height">
              <v-list-item v-for="mentor in mentors" :key="mentor.id" @click="selectMentor(mentor)" class="mentor-item">
                <v-list-item-avatar>
                  <v-img :src="mentor.avatar"></v-img>
                </v-list-item-avatar>
                <v-list-item-content>
                  <v-list-item-title>{{ mentor.name }}</v-list-item-title>
                  <v-list-item-subtitle>{{ mentor.lastMessage }}</v-list-item-subtitle>
                </v-list-item-content>
              </v-list-item>
            </v-list>
            <v-btn class="mt-4 ml-2" @click="toggleStrobe" :color="isStrobing ? 'error' : 'warning'">
              {{ isStrobing ? 'Stop Strobe' : 'Simulate Unfocused' }}
            </v-btn>
          </v-col>
          <v-col cols="8" style="background-color: #111b21;" class="d-flex flex-column fill-height">
            <div v-if="selectedMentor" class="d-flex flex-column fill-height">
              <v-toolbar flat dark>
                <v-app-bar-nav-icon></v-app-bar-nav-icon>
                <v-toolbar-title>{{ selectedMentor.name }}</v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn icon>
                  <v-icon>mdi-video</v-icon>
                </v-btn>
                <v-btn icon>
                  <v-icon>mdi-phone</v-icon>
                </v-btn>
                <v-btn icon>
                  <v-icon>mdi-dots-vertical</v-icon>
                </v-btn>
              </v-toolbar>
              <v-divider></v-divider>
              <v-container class="flex-grow-1 overflow-y-auto chat-container fill-height">
                <div v-for="message in messages" :key="message.id" :class="{'message-sent': message.sender === 'me', 'message-received': message.sender === 'mentor'}">
                  <v-chip
                    :color="message.sender === 'me' ? '#dcf8c6' : '#2a3942'"
                    :text-color="message.sender === 'me' ? 'black' : 'white'"
                    rounded="xl"
                    class="message-bubble"
                  >
                    {{ message.text }}
                  </v-chip>
                </div>
              </v-container>
              <v-footer flat style="background-color: #232d36;">
                <v-text-field
                  v-model="newMessage"
                  outlined
                  placeholder="Type a message"
                  class="flex-grow-1 mr-2 message-input"
                  hide-details
                  solo
                  dark
                  @keyup.enter="sendMessage"
                ></v-text-field>
                <v-btn color="#00a884" @click="sendMessage" rounded="circle" height="48" width="48">
                  <v-icon>mdi-send</v-icon>
                </v-btn>
              </v-footer>
            </div>
            <div v-else class="d-flex align-center justify-center fill-height">
              <v-subheader style="color: #8696a0;">Select a mentor to start chatting</v-subheader>
            </div>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'ChatInterface',
  data() {
    return {
      mentors: [
        { id: 1, name: 'Alice', avatar: 'https://via.placeholder.com/150/77b1d9', lastMessage: 'How\'s your progress?' },
        { id: 2, name: 'Bob', avatar: 'https://via.placeholder.com/150/f06292', lastMessage: 'Let me know if you need help.' },
        { id: 3, name: 'Charlie', avatar: 'https://via.placeholder.com/150/64b5f6', lastMessage: 'Great work!' },
      ],
      selectedMentor: ref(null),
      messages: ref([]),
      newMessage: ref(''),
      nextMessageId: 1,
      isStrobing: ref(false),
      strobeInterval: null,
    };
  },
  methods: {
    selectMentor(mentor) {
      this.selectedMentor = mentor;
      this.messages.value = [
        { id: 0, sender: 'mentor', text: 'Hello!' },
      ];
      this.nextMessageId = 1;
    },
    sendMessage() {
      if (this.newMessage.trim() !== '' && this.selectedMentor) {
        this.messages.value.push({ id: this.nextMessageId++, sender: 'me', text: this.newMessage });
        this.newMessage = '';
      }
    },
    toggleStrobe() {
      this.isStrobing = !this.isStrobing;
      if (this.isStrobing) {
        this.startStrobe();
      } else {
        this.stopStrobe();
      }
    },
    startStrobe() {
      let isBlack = false;
      this.strobeInterval = setInterval(() => {
        const appRoot = document.getElementById('app-root');
        if (appRoot) {
          appRoot.style.backgroundColor = isBlack ? 'white' : 'black';
        }
        isBlack = !isBlack;
      }, 100); // Adjust the interval for faster/slower flashing
    },
    stopStrobe() {
      clearInterval(this.strobeInterval);
      const appRoot = document.getElementById('app-root');
      if (appRoot) {
        appRoot.style.backgroundColor = ''; // Reset background color
      }
    },
  },
  onUnmounted() {
    this.stopStrobe(); // Clear interval when component unmounts
  },
};
</script>

<style scoped>
.mentor-item {
  cursor: pointer;
}

.chat-container {
  padding: 16px;
  display: flex;
  flex-direction: column;
}

.message-sent {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.message-received {
  display: flex;
  justify-content: flex-start;
  margin-bottom: 8px;
}

.message-bubble {
  max-width: 80%;
  white-space: normal;
  padding: 8px 12px;
}

.message-input >>> .v-input__control {
  border-radius: 24px;
}

/* The 'strobe' class will handle the transition, but the actual background color change is done directly */
.strobe * {
  transition: background-color 0.1s ease-in-out, color 0.1s ease-in-out; /* Smooth transition */
}
</style>