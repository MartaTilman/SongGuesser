<template>
  <div class="page">
    <div class="container">
      <h1>Lobby</h1>
      <div class="lobby-code-card">
        <span class="code-label">Kod za dijeljenje</span>
        <strong class="code-value">{{ store.lobbyId }}</strong>
      </div>

      <p>Igrač: {{ store.playerName }}</p>
      <p v-if="store.connected" class="ok">Spojeno na server</p>
      <p v-else class="warn">Spajanje...</p>

      <div class="grid">
        <PlayerList :players="store.players" :host="store.host" />

        <div class="card">
          <h3>Kontrole</h3>
          <button v-if="store.isHost" type="button" @click="store.startRound()">
            Pokreni rundu
          </button>
          <p v-else>Čekanje hosta da pokrene igru...</p>

          <button class="secondary" type="button" @click="copyLobbyCode">
            Kopiraj kod
          </button>

          <button class="secondary" type="button" @click="goBlockchain">
            Pregled blockchaina
          </button>

          <p v-if="copyMessage" class="copy-message">{{ copyMessage }}</p>
        </div>
      </div>

      <div v-if="store.error" class="card error-box">
        {{ store.error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import PlayerList from "../components/PlayerList.vue";

const router = useRouter();
const route = useRoute();
const store = useGameStore();
const copyMessage = ref("");

onMounted(async () => {
  if (!store.lobbyId || !store.playerName) {
    await router.replace({ name: "home" });
    return;
  }

  try {
    await store.fetchLobbyInfo();
  } catch (error) {
    console.error("Lobby info fetch failed:", error);
    store.error = "Ne mogu dohvatiti informacije o lobbyju.";
  }
});

watch(
  () => store.phase,
  async (phase) => {
    if (phase === "round" && route.name !== "game") {
      await router.replace({ name: "game" });
    }
  },
  { flush: "post" }
);

async function goBlockchain() {
  if (route.name !== "blockchain") {
    await router.replace({ name: "blockchain" });
  }
}

async function copyLobbyCode() {
  try {
    await navigator.clipboard.writeText(store.lobbyId);
    copyMessage.value = "Kod je kopiran.";
  } catch (error) {
    copyMessage.value = "Ne mogu kopirati kod.";
  }
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 30px;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

.lobby-code-card {
  display: inline-flex;
  flex-direction: column;
  gap: 6px;
  margin: 12px 0 18px;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 14px;
  padding: 14px 18px;
}

.code-label {
  color: #9ca3af;
  font-size: 14px;
}

.code-value {
  font-size: 28px;
  letter-spacing: 0.14em;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

button {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #16a34a;
  color: white;
}

.secondary {
  margin-top: 12px;
  background: #374151;
}

.ok {
  color: #4ade80;
}

.warn {
  color: #facc15;
}

.copy-message {
  margin-top: 12px;
  color: #93c5fd;
}

.error-box {
  margin-top: 20px;
  color: #f87171;
}
</style>
