<template>
  <div class="page">
    <div class="container">
      <h1 v-if="store.phase === 'finished' && !showFullFinalLeaderboard">Pobjednici</h1>
      <h1 v-else-if="store.phase === 'finished'">Konačni leaderboard</h1>
      <h1 v-else>Rezultati runde</h1>

      <div v-if="store.phase !== 'finished'">
        <LeaderboardTable :leaderboard="roundBoard" title="Poredak nakon runde" />

        <div class="card answer-card">
          <h3>Točni odgovori</h3>
          <div class="answer-grid">
            <div class="answer-item">
              <span class="label">Naziv pjesme</span>
              <strong>{{ store.roundData?.correct_title }}</strong>
            </div>
            <div class="answer-item">
              <span class="label">Izvođač</span>
              <strong>{{ store.roundData?.correct_artist }}</strong>
            </div>
            <div class="answer-item">
              <span class="label">Godina</span>
              <strong>{{ store.roundData?.correct_year }}</strong>
            </div>
          </div>
        </div>

        <div class="card" v-if="store.awardedPoints.length">
          <h3>Gdje su igrači pogodili ili pogriješili</h3>
          <div class="result-list">
            <div v-for="item in sortedAwardedPoints" :key="item.name" class="result-row">
              <div class="result-header">
                <strong>{{ item.name }}</strong>
                <span class="points">+{{ item.gained_points }}</span>
              </div>
              <div class="result-statuses">
                <span :class="item.title_correct ? 'ok' : 'bad'">
                  Naziv: {{ item.title_correct ? "točno" : "netočno" }}
                </span>
                <span :class="item.artist_correct ? 'ok' : 'bad'">
                  Izvođač: {{ item.artist_correct ? "točno" : "netočno" }}
                </span>
                <span :class="item.year_correct ? 'ok' : 'bad'">
                  Godina: {{ item.year_correct ? "točno" : "netočno" }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else>
        <div v-if="!showFullFinalLeaderboard" class="podium">
          <div
            v-for="(player, index) in topThree"
            :key="player.name"
            class="podium-card"
            :class="`place-${index + 1}`"
          >
            <div class="place">#{{ index + 1 }}</div>
            <div class="avatar">{{ player.avatar || "🎵" }}</div>
            <strong>{{ player.name }}</strong>
            <span>{{ player.score }} bodova</span>
          </div>
        </div>

        <LeaderboardTable
          v-else
          :leaderboard="finalBoard"
          title="Konačni poredak"
        />
      </div>

      <div class="actions">
        <button v-if="store.phase !== 'finished' && store.isHost" type="button" @click="nextSong">
          Next
        </button>
        <button
          v-if="store.phase === 'finished' && !showFullFinalLeaderboard"
          type="button"
          @click="showFullFinalLeaderboard = true"
        >
          Next
        </button>
        <button type="button" @click="goBlockchain">Blockchain</button>
        <button v-if="store.phase === 'finished'" type="button" @click="goHome">Početna</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import LeaderboardTable from "../components/LeaderboardTable.vue";

const router = useRouter();
const store = useGameStore();
const showFullFinalLeaderboard = ref(false);

const roundBoard = computed(() => {
  return [...store.leaderboard].sort((a, b) => b.score - a.score);
});

const finalBoard = computed(() => {
  return [...store.finalLeaderboard].sort((a, b) => b.score - a.score);
});

const topThree = computed(() => {
  return finalBoard.value.slice(0, 3);
});

const sortedAwardedPoints = computed(() => {
  return [...store.awardedPoints].sort((a, b) => b.total_score - a.total_score);
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

    if (phase !== "finished") {
      showFullFinalLeaderboard.value = false;
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

.answer-card {
  margin-top: 20px;
}

.answer-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}

.answer-item {
  background: #111827;
  border-radius: 12px;
  padding: 14px;
}

.label {
  display: block;
  margin-bottom: 8px;
  color: #9ca3af;
  font-size: 14px;
}

.result-list {
  display: grid;
  gap: 12px;
}

.result-row {
  background: #111827;
  border-radius: 12px;
  padding: 14px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.result-statuses {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.points {
  color: #facc15;
  font-weight: 700;
}

.ok {
  color: #4ade80;
}

.bad {
  color: #f87171;
}

.podium {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 20px;
}

.podium-card {
  background: #1f2937;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.place-1 {
  border: 2px solid #facc15;
}

.place-2 {
  border: 2px solid #d1d5db;
}

.place-3 {
  border: 2px solid #d97706;
}

.place {
  font-size: 24px;
  font-weight: 700;
}

.avatar {
  font-size: 42px;
}

.actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

button {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
}
</style>
