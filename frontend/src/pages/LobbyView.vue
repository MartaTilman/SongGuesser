<template>
  <div class="page">
    <div class="container">
      <h1>Lobby: {{ store.lobbyId }}</h1>
      <p>Igrač: {{ store.playerName }}</p>
      <p v-if="store.connected" class="ok">Spojeno na server</p>
      <p v-else class="warn">Spajanje...</p>

      <div class="grid">
        <PlayerList :players="store.players" :host="store.host" />

        <div class="card">
          <h3>Kontrole</h3>
          <button v-if="store.isHost" @click="store.startRound()">Pokreni rundu</button>
          <p v-else>Čekanje hosta da pokrene igru...</p>

          <button class="secondary" @click="goBlockchain">Pregled blockchaina</button>
        </div>
      </div>

      <div v-if="store.error" class="card error-box">
        {{ store.error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import PlayerList from "../components/PlayerList.vue";

const router = useRouter();
const store = useGameStore();

onMounted(async () => {
  if (!store.lobbyId || !store.playerName) {
    router.push("/");
    return;
  }

  await store.fetchLobbyInfo();
});

watch(
  () => store.phase,
  (phase) => {
    if (phase === "round") {
      router.push("/game");
    }
  }
);

function goBlockchain() {
  router.push("/blockchain");
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

.error-box {
  margin-top: 20px;
  color: #f87171;
}
</style>