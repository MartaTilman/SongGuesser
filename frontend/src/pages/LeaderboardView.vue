<template>
  <div class="page">
    <div class="container">
      <h1 v-if="store.phase === 'finished'">Konačni rezultat</h1>
      <h1 v-else>Rezultati pjesme</h1>

      <LeaderboardTable :leaderboard="currentBoard" />

      <div class="card" v-if="store.phase !== 'finished'">
        <h3>Točan odgovor</h3>
        <p>{{ store.roundData?.correct_title }} — {{ store.roundData?.correct_artist }}</p>
      <p>
  {{ store.roundData?.correct_title }} — {{ store.roundData?.correct_artist }} — {{ store.roundData?.correct_year }}
</p>
    </div>

      <div class="card" v-if="store.awardedPoints.length && store.phase !== 'finished'">
        <h3>Detalji odgovora</h3>
        <ul>
          <li v-for="item in store.awardedPoints" :key="item.name">
            {{ item.name }} — "{{ item.answer }}" — {{ item.correct ? "točno" : "netočno" }} — +{{ item.gained_points }}
          </li>
        </ul>
      </div>

      <div class="actions">
        <button v-if="store.phase !== 'finished' && store.isHost" @click="nextSong">Pokreni sljedeću pjesmu</button>
        <button @click="goBlockchain">Blockchain</button>
        <button v-if="store.phase === 'finished'" @click="goHome">Početna</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import LeaderboardTable from "../components/LeaderboardTable.vue";

const router = useRouter();
const store = useGameStore();

const currentBoard = computed(() => {
  return store.phase === "finished" ? store.finalLeaderboard : store.leaderboard;
});

function nextSong() {
  store.startRound();
  router.push("/game");
}

function goBlockchain() {
  router.push("/blockchain");
}

function goHome() {
  store.clearAll();
  router.push("/");
}

watch(
  () => store.phase,
  (phase) => {
    if (phase === "round") {
      router.push("/game");
    }
  }
);
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

.card {
  margin-top: 20px;
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
}

button {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
}
</style>