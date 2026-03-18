<template>
  <div class="page">
    <div class="container">
      <h1>Music Blockchain Quiz</h1>
      <p>Unesi ime i lobby ID za ulazak u igru.</p>

      <div class="form-card">
        <input v-model="playerName" type="text" placeholder="Ime igrača" />
        <input v-model="lobbyId" type="text" placeholder="Lobby ID" />
        <AvatarPicker v-model="avatar" />

        <button @click="joinLobby">Uđi u lobby</button>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import AvatarPicker from "../components/AvatarPicker.vue";

const router = useRouter();
const store = useGameStore();

const playerName = ref("");
const lobbyId = ref("");
const avatar = ref("🎵");
const error = ref("");

function joinLobby() {
  if (!playerName.value.trim() || !lobbyId.value.trim()) {
    error.value = "Unesi ime i lobby ID.";
    return;
  }

  store.setUserData({
    playerName: playerName.value.trim(),
    lobbyId: lobbyId.value.trim(),
    avatar: avatar.value
  });

  store.connect();
  router.push("/lobby");
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}

.container {
  width: 100%;
  max-width: 500px;
  padding: 20px;
}

.form-card {
  background: #1f2937;
  padding: 24px;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

input {
  padding: 14px;
  border: none;
  border-radius: 10px;
}

button {
  padding: 14px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
  font-weight: bold;
}

.error {
  color: #f87171;
}
</style>