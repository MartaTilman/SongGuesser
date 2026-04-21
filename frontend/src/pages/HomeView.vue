<template>
  <div class="page">
    <div class="container">
      <h1>Music Blockchain Quiz</h1>
      <p>Kreiraj novi lobby s automatskim kodom ili se pridruži postojećem kodom.</p>

      <div class="mode-switch">
        <button
          type="button"
          :class="{ active: mode === 'create' }"
          @click="mode = 'create'"
        >
          Kreiraj lobby
        </button>
        <button
          type="button"
          :class="{ active: mode === 'join' }"
          @click="mode = 'join'"
        >
          Pridruži se
        </button>
      </div>

      <div class="form-card">
        <input v-model="playerName" type="text" placeholder="Ime igrača" />

        <input
          v-if="mode === 'join'"
          v-model="lobbyId"
          type="text"
          placeholder="Unesi lobby kod"
        />

        <div v-else class="generated-box">
          <span class="generated-label">Lobby kod će se generirati automatski</span>
        </div>

        <AvatarPicker v-model="avatar" />

        <button type="button" class="primary-btn" :disabled="loading" @click="submit">
          {{ loading ? "Učitavanje..." : mode === "create" ? "Kreiraj i uđi" : "Uđi u lobby" }}
        </button>

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

const mode = ref("create");
const playerName = ref("");
const lobbyId = ref("");
const avatar = ref("🎵");
const error = ref("");
const loading = ref(false);

async function submit() {
  error.value = "";

  if (!playerName.value.trim()) {
    error.value = "Unesi ime igrača.";
    return;
  }

  if (mode.value === "join" && !lobbyId.value.trim()) {
    error.value = "Unesi lobby kod.";
    return;
  }

  loading.value = true;

  try {
    if (mode.value === "create") {
      await store.createLobby(playerName.value.trim(), avatar.value);
    } else {
      await store.joinExistingLobby(playerName.value.trim(), lobbyId.value.trim(), avatar.value);
    }

    store.connect();
    await router.push("/lobby");
  } catch (err) {
    error.value =
      err?.response?.data?.detail ||
      err?.message ||
      "Neuspješno spajanje na lobby.";
  } finally {
    loading.value = false;
  }
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
  max-width: 560px;
  padding: 20px;
}

.mode-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 20px 0 14px;
}

.mode-switch button {
  padding: 12px 16px;
  border: 1px solid #374151;
  border-radius: 12px;
  background: #111827;
  color: #e5e7eb;
  font-weight: 700;
}

.mode-switch button.active {
  background: #2563eb;
  border-color: #2563eb;
  color: white;
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

.generated-box {
  padding: 14px;
  border-radius: 10px;
  background: #111827;
  border: 1px dashed #4b5563;
}

.generated-label {
  color: #d1d5db;
}

.primary-btn {
  padding: 14px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
  font-weight: bold;
}

.primary-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.error {
  color: #f87171;
}
</style>
