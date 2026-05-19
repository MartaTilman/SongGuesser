<template>
  <div class="page">
    <div class="container">
      <div class="top-code">
        <span class="top-code-label">LOBBY ID</span>
        <strong class="top-code-value">{{ store.lobbyId }}</strong>
      </div>

      <div v-if="store.phase !== 'finished'" class="panel">
        <div v-if="store.awardedPoints.length" class="answers-card">
          <div class="answers-header">
            <span></span>
            <span>Your answer</span>
          </div>

          <div v-for="item in sortedAwardedPoints" :key="item.name" class="answer-player">
            <div class="answer-grid">
              <div class="answer-label">Song title was "{{ store.roundData?.correct_title }}"</div>
              <div class="answer-value">
                <span>{{ item.title_answer || "-" }}</span>
                <strong :class="item.title_correct ? 'gain' : 'zero'">+{{ item.title_correct ? Math.round(item.gained_points / (item.year_correct + item.artist_correct + item.title_correct || 1)) : 0 }}</strong>
              </div>
              <div class="answer-label">Artist was "{{ store.roundData?.correct_artist }}"</div>
              <div class="answer-value">
                <span>{{ item.artist_answer || "-" }}</span>
                <strong :class="item.artist_correct ? 'gain' : 'zero'">+{{ item.artist_correct ? Math.round(item.gained_points / (item.year_correct + item.artist_correct + item.title_correct || 1)) : 0 }}</strong>
              </div>
              <div class="answer-label">Year was "{{ store.roundData?.correct_year }}"</div>
              <div class="answer-value">
                <span>{{ item.year_answer || "-" }}</span>
                <strong :class="item.year_correct ? 'gain' : 'zero'">+{{ item.year_correct ? Math.round(item.gained_points / (item.year_correct + item.artist_correct + item.title_correct || 1)) : 0 }}</strong>
              </div>
            </div>

            <div class="player-total">
              <div class="player-total-left">
                <span class="player-avatar">{{ findAvatar(item.name) }}</span>
                <span>{{ item.name }}</span>
              </div>
              <strong>{{ item.total_score }}</strong>
            </div>
          </div>
        </div>

        <LeaderboardTable :leaderboard="roundBoard" :title="''" />

        <div class="actions">
          <button v-if="store.isHost" type="button" @click="nextSong">Next</button>
          <p v-else class="waiting-text">Waiting for host...</p>
        </div>
      </div>

      <div v-else class="panel final-panel">
        <div v-if="!showFullFinalLeaderboard" class="podium">
          <div class="place-label second-label">#2</div>
          <div class="place-label first-label">#1</div>
          <div class="place-label third-label">#3</div>

          <div v-if="topThree[1]" class="podium-card second">
            <div class="podium-avatar">{{ topThree[1].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[1].name }}</div>
          </div>

          <div v-if="topThree[0]" class="podium-card first">
            <div class="podium-avatar">{{ topThree[0].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[0].name }}</div>
          </div>

          <div v-if="topThree[2]" class="podium-card third">
            <div class="podium-avatar">{{ topThree[2].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[2].name }}</div>
          </div>
        </div>

        <LeaderboardTable
          v-else
          :leaderboard="finalBoard"
          :title="''"
        />

        <div class="actions final-actions">
          <button
            v-if="!showFullFinalLeaderboard"
            type="button"
            @click="showFullFinalLeaderboard = true"
          >
            Next
          </button>
          <template v-else>
            <button type="button" @click="goLobby">Lobby</button>
            <button type="button" @click="goHome">Exit</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import LeaderboardTable from "../components/LeaderboardTable.vue";

const router = useRouter();
const store = useGameStore();
const showFullFinalLeaderboard = ref(false);

let audioContext = null;

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

function findAvatar(name) {
  return store.players.find((player) => player.name === name)?.avatar || "🎵";
}

function nextSong() {
  store.startRound();
  router.push("/game");
}

function goLobby() {
  store.resetGame();
  router.push("/lobby");
}

function goHome() {
  store.clearAll();
  router.push("/");
}

function ensureAudioContext() {
  if (typeof window === "undefined") return null;

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return null;

  if (!audioContext || audioContext.state === "closed") {
    audioContext = new AudioContextClass();
  }

  if (audioContext.state === "suspended") {
    audioContext.resume().catch(() => {});
  }

  return audioContext;
}

function playLeaderboardSound() {
  const context = ensureAudioContext();
  if (!context) return;

  const nowTime = context.currentTime;
  const gainNode = context.createGain();
  gainNode.connect(context.destination);

  gainNode.gain.setValueAtTime(0.0001, nowTime);
  gainNode.gain.exponentialRampToValueAtTime(0.16, nowTime + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, nowTime + 0.8);

  const notes = [523.25, 659.25, 783.99];

  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    oscillator.type = "triangle";
    oscillator.frequency.setValueAtTime(frequency, nowTime + index * 0.14);
    oscillator.connect(gainNode);
    oscillator.start(nowTime + index * 0.14);
    oscillator.stop(nowTime + index * 0.14 + 0.22);
  });
}

onMounted(() => {
  setTimeout(() => {
    playLeaderboardSound();
  }, 80);
});

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
  padding: 28px 10px 20px;
}

.container {
  width: min(100%, 690px);
  margin: 0 auto;
}

.top-code {
  display: grid;
  grid-template-columns: auto auto;
  gap: 18px;
  align-items: center;
  width: min(100%, 260px);
  padding: 14px 22px;
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(218, 233, 255, 0.96));
  color: #0b2563;
  font-style: italic;
  font-weight: 800;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 4px 12px rgba(44, 84, 150, 0.12);
}

.top-code-label {
  font-size: 14px;
}

.top-code-value {
  font-size: 17px;
}

.panel {
  margin-top: 10px;
  padding: 18px 18px 24px;
  background: var(--panel);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-radius: 28px;
  box-shadow: var(--shadow-soft);
}

.answers-card {
  margin-bottom: 18px;
}

.answers-header {
  display: grid;
  grid-template-columns: 1fr 1fr;
  margin: 0 8px 12px;
  color: var(--text-blue);
  font-size: 17px;
  font-style: italic;
  text-align: center;
}

.answer-player + .answer-player {
  margin-top: 14px;
}

.answer-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 12px;
}

.answer-label,
.answer-value,
.player-total {
  min-height: 44px;
  padding: 11px 18px;
  background: rgba(238, 245, 255, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 14px;
  color: #123a84;
  font-size: 16px;
  font-style: italic;
  font-weight: 800;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
}

.player-total {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(218, 233, 255, 0.96));
  color: #0b2563;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 4px 12px rgba(44, 84, 150, 0.12);
}

.answer-value {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(218, 233, 255, 0.96));
  color: #0b2563;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 4px 12px rgba(44, 84, 150, 0.12);
}

.answer-value span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.gain {
  color: #087a2e;
}

.zero {
  color: #b42336;
}

.player-total {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 14px;
}

.player-total-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.player-avatar {
  font-size: 22px;
}

.actions {
  margin-top: 18px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.final-actions {
  justify-content: space-between;
}

button {
  min-width: 138px;
  padding: 15px 24px;
  border: 0;
  border-radius: 16px;
  background: linear-gradient(180deg, #83a8ff 0%, #6f96fd 100%);
  color: white;
  font-size: 18px;
  font-style: italic;
  font-weight: 800;
}

.waiting-text {
  width: 100%;
  margin: 0;
  text-align: center;
  color: var(--text-blue);
  font-size: 18px;
  font-style: italic;
}

.final-panel {
  min-height: 460px;
}

.podium {
  position: relative;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  align-items: end;
  gap: 18px;
  min-height: 330px;
  padding: 48px 36px 10px;
}

.place-label {
  position: absolute;
  color: var(--text-blue-strong);
  font-size: 58px;
  font-style: italic;
  font-weight: 500;
}

.first-label {
  top: 14px;
  left: 50%;
  transform: translateX(-50%);
}

.second-label {
  top: 104px;
  left: 82px;
}

.third-label {
  top: 154px;
  right: 86px;
}

.podium-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 14px 14px 0 0;
  color: white;
  text-align: center;
  box-shadow: inset 0 -40px 55px rgba(255, 255, 255, 0.32);
}

.podium-card.first {
  height: 240px;
  background: linear-gradient(180deg, #c12be5 0%, #e05cc8 100%);
}

.podium-card.second {
  height: 170px;
  background: linear-gradient(180deg, #ffe179 0%, #ffd767 100%);
}

.podium-card.third {
  height: 120px;
  background: linear-gradient(180deg, #ff3ba9 0%, #ff4fa1 100%);
}

.podium-avatar {
  font-size: 44px;
}

.podium-name {
  margin-top: 10px;
  font-size: 22px;
  font-style: italic;
  font-weight: 800;
}

@media (max-width: 720px) {
  .panel {
    padding: 14px 12px 18px;
  }

  .answer-grid {
    grid-template-columns: 1fr;
  }

  .podium {
    grid-template-columns: 1fr;
    gap: 12px;
    min-height: auto;
    padding: 18px 8px 10px;
  }

  .place-label {
    display: none;
  }

  .podium-card {
    border-radius: 16px;
    height: 140px !important;
  }
}
</style>
