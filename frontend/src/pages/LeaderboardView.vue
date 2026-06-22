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
          <button v-if="isFinalRoundLeaderboard" type="button" @click="showFinalResults">
            Next
          </button>
          <button v-else-if="store.isHost" type="button" @click="nextSong">Next</button>
          <p v-else class="waiting-text">Waiting for host...</p>
        </div>
      </div>

      <div v-else class="panel final-panel">
        <div v-if="!showFullFinalLeaderboard" class="podium" :style="{ '--podium-cols': topThree.length }">
          <div v-if="isPodiumRankVisible(2) && topThree[1]" class="podium-card second" :class="{ 'solo': topThree.length === 1, 'duo': topThree.length === 2 }">
            <div class="place-label">#2</div>
            <div class="podium-avatar">{{ topThree[1].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[1].name }}</div>
            <div class="podium-score">{{ topThree[1].score }}</div>
          </div>

          <div v-if="isPodiumRankVisible(1) && topThree[0]" class="podium-card first" :class="{ 'solo': topThree.length === 1, 'duo': topThree.length === 2 }">
            <div class="place-label">#1</div>
            <div class="podium-avatar">{{ topThree[0].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[0].name }}</div>
            <div class="podium-score">{{ topThree[0].score }}</div>
          </div>

          <div v-if="isPodiumRankVisible(3) && topThree[2]" class="podium-card third">
            <div class="place-label">#3</div>
            <div class="podium-avatar">{{ topThree[2].avatar || "🎵" }}</div>
            <div class="podium-name">{{ topThree[2].name }}</div>
            <div class="podium-score">{{ topThree[2].score }}</div>
          </div>
        </div>

        <LeaderboardTable
          v-else
          :leaderboard="finalBoard"
          :title="''"
        />

        <div class="actions final-actions">
          <button
            v-if="!showFullFinalLeaderboard && showPodiumReveal"
            type="button"
            @click="showFullFinalLeaderboard = true"
          >
            Next
          </button>
          <template v-else-if="showFullFinalLeaderboard">
            <button type="button" @click="goLobby">Lobby</button>
            <button type="button" @click="goHome">Exit</button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import LeaderboardTable from "../components/LeaderboardTable.vue";

const router = useRouter();
const store = useGameStore();
const showFullFinalLeaderboard = ref(false);
const showPodiumReveal = ref(false);
const visiblePodiumRanks = ref([]);

let audioContext = null;
let podiumRevealTimers = [];
let drumRollAudio = null;
let removeDrumRollUnlockListeners = null;
const drumRollAudioSrc = "/drum-roll.mp3";

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

const isFinalRoundLeaderboard = computed(() => {
  return store.phase === "leaderboard" && store.finalResultsReady;
});

function findAvatar(name) {
  return store.players.find((player) => player.name === name)?.avatar || "🎵";
}

function isPodiumRankVisible(rank) {
  return visiblePodiumRanks.value.includes(rank);
}

function nextSong() {
  store.startRound();
  router.push("/game");
}

function showFinalResults() {
  store.showFinalResults();
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

function playDrumRollSound() {
  if (typeof Audio === "undefined") return Promise.resolve();

  if (!drumRollAudio) {
    drumRollAudio = new Audio(drumRollAudioSrc);
    drumRollAudio.preload = "auto";
    drumRollAudio.volume = 0.72;
  }

  return new Promise((resolve) => {
    let resolved = false;
    const fallbackTimer = setTimeout(() => finish(), 4500);

    const finish = () => {
      if (resolved) return;
      resolved = true;
      clearTimeout(fallbackTimer);
      drumRollAudio.removeEventListener("ended", finish);
      drumRollAudio.removeEventListener("error", finish);
      resolve();
    };

    drumRollAudio.pause();
    drumRollAudio.currentTime = 0;
    drumRollAudio.addEventListener("ended", finish, { once: true });
    drumRollAudio.addEventListener("error", finish, { once: true });

    drumRollAudio.play().catch(() => {
      setupDrumRollUnlock();
      finish();
    });
  });
}

function clearPodiumRevealTimers() {
  podiumRevealTimers.forEach((timer) => clearTimeout(timer));
  podiumRevealTimers = [];
}

function setupDrumRollUnlock() {
  if (typeof window === "undefined" || removeDrumRollUnlockListeners) return;

  const unlockDrumRoll = () => {
    removeDrumRollUnlockListeners?.();
    removeDrumRollUnlockListeners = null;
    playDrumRollSound();
  };

  const events = ["pointerdown", "touchstart", "keydown"];

  events.forEach((eventName) => {
    window.addEventListener(eventName, unlockDrumRoll, { once: true, passive: true });
  });

  removeDrumRollUnlockListeners = () => {
    events.forEach((eventName) => {
      window.removeEventListener(eventName, unlockDrumRoll);
    });
  };
}

async function revealPodiumWithDrumRoll() {
  clearPodiumRevealTimers();
  showPodiumReveal.value = false;
  visiblePodiumRanks.value = [];
  await playDrumRollSound();

  const revealOrder = [3, 2, 1].filter((rank) => topThree.value[rank - 1]);

  revealOrder.forEach((rank, index) => {
    const timer = setTimeout(() => {
      visiblePodiumRanks.value = [...visiblePodiumRanks.value, rank];
    }, index * 720);

    podiumRevealTimers.push(timer);
  });

  const finishTimer = setTimeout(() => {
    showPodiumReveal.value = true;
    playLeaderboardSound();
  }, revealOrder.length * 720);

  podiumRevealTimers.push(finishTimer);
}

onMounted(() => {
  if (store.phase === "finished") {
    revealPodiumWithDrumRoll();
  } else {
    setTimeout(() => {
      playLeaderboardSound();
    }, 80);
  }
});

onBeforeUnmount(() => {
  clearPodiumRevealTimers();
  removeDrumRollUnlockListeners?.();
  removeDrumRollUnlockListeners = null;
});

watch(
  () => store.phase,
  (phase) => {
    if (phase === "round") {
      router.push("/game");
    }

    if (phase !== "finished") {
      showFullFinalLeaderboard.value = false;
      showPodiumReveal.value = false;
      visiblePodiumRanks.value = [];
      clearPodiumRevealTimers();
      return;
    }

    revealPodiumWithDrumRoll();
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
  min-width: 0;
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
  min-width: 0;
  overflow-wrap: anywhere;
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
  grid-template-columns: repeat(var(--podium-cols, 3), 1fr);
  align-items: end;
  gap: 16px;
  min-height: 330px;
  padding: 28px 28px 14px;
  border: 1px solid rgba(58, 112, 196, 0.34);
  border-radius: 18px;
  background:
    linear-gradient(180deg, rgba(237, 247, 255, 0.92), rgba(169, 207, 247, 0.54)),
    repeating-linear-gradient(90deg, rgba(24, 86, 178, 0.1) 0 1px, transparent 1px 22px);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    inset 0 -18px 34px rgba(47, 119, 212, 0.16);
}

.place-label {
  position: static;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  min-height: 50px;
  margin-bottom: 14px;
  padding: 4px 12px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-blue-strong);
  font-size: 36px;
  font-style: italic;
  font-weight: 900;
  transform-origin: center bottom;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.95),
    0 6px 14px rgba(29, 76, 148, 0.14);
}

.podium-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
  padding: 18px 12px 16px;
  border: 1px solid rgba(255, 255, 255, 0.86);
  border-radius: 8px 8px 0 0;
  color: #07377e;
  text-align: center;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.66);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    inset 0 -34px 48px rgba(24, 87, 184, 0.2),
    0 12px 18px rgba(27, 65, 128, 0.18);
  opacity: 0;
  transform: translateY(28px) scaleY(0.74) scaleX(0.96);
  transform-origin: center bottom;
  animation: xpWindowOpen 0.62s cubic-bezier(0.15, 1.18, 0.38, 1) forwards;
}

.podium-card.first {
  grid-column: 2;
  height: 240px;
  background: linear-gradient(180deg, #ffffff 0%, #d7f0ff 18%, #70c6ff 54%, #2d76da 100%);
  animation-delay: 0.08s;
}

.podium-card.first.solo {
  grid-column: 1;
}

.podium-card.second {
  grid-column: 1;
  grid-row: 1;
  height: 170px;
  background: linear-gradient(180deg, #ffffff 0%, #edf7ff 20%, #9bd7ff 58%, #5595e7 100%);
  animation-delay: 0.2s;
}

.podium-card.third {
  grid-column: 3;
  grid-row: 1;
  height: 120px;
  background: linear-gradient(180deg, #ffffff 0%, #f0f8ff 22%, #b5e3ff 60%, #72a9ed 100%);
  animation-delay: 0.3s;
}

.podium-avatar {
  font-size: 42px;
}

.podium-name {
  margin-top: 10px;
  font-size: 22px;
  font-style: italic;
  font-weight: 800;
  overflow-wrap: anywhere;
  opacity: 0;
  animation: xpNameGlow 0.52s ease-out forwards;
  animation-delay: 0.34s;
}

.podium-score {
  margin-top: 8px;
  color: #174d9d;
  font-size: 16px;
  font-style: italic;
  font-weight: 900;
}

.podium-card.second .podium-name {
  animation-delay: 0.46s;
}

.podium-card.third .podium-name {
  animation-delay: 0.56s;
}

@keyframes xpWindowOpen {
  0% {
    opacity: 0;
    transform: translateY(28px) scaleY(0.74) scaleX(0.96);
    filter: brightness(1.25) saturate(1.25);
  }

  58% {
    opacity: 1;
    transform: translateY(-8px) scaleY(1.04) scaleX(1.02);
    filter: brightness(1.12) saturate(1.12);
  }

  100% {
    opacity: 1;
    transform: translateY(0) scaleY(1) scaleX(1);
    filter: brightness(1) saturate(1);
  }
}

@keyframes xpNameGlow {
  0% {
    opacity: 0;
    transform: translateY(8px);
    text-shadow: 0 0 14px rgba(255, 255, 255, 0.95);
  }

  100% {
    opacity: 1;
    transform: translateY(0);
    text-shadow: 0 1px 0 rgba(255, 255, 255, 0.66);
  }
}

@media (max-width: 720px) {
  .page {
    padding: 12px 0 16px;
  }

  .panel {
    padding: 14px 12px 18px;
    border-radius: 18px;
  }

  .answer-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  .answers-header {
    display: none;
  }

  .answer-label,
  .answer-value,
  .player-total {
    padding: 10px 12px;
    border-radius: 12px;
    font-size: 14px;
  }

  .answer-value {
    align-items: flex-start;
  }

  .podium {
    grid-template-columns: 1fr;
    gap: 12px;
    min-height: auto;
    padding: 18px 8px 10px;
  }

  .podium-card {
    grid-column: auto !important;
    grid-row: auto !important;
    border-radius: 16px;
    height: auto !important;
    min-height: 132px;
    padding: 14px 12px;
  }

  .place-label {
    min-width: 58px;
    min-height: 38px;
    margin-bottom: 8px;
    font-size: 26px;
  }

  .actions,
  .final-actions {
    justify-content: stretch;
    gap: 10px;
  }

  button {
    flex: 1;
    min-width: 0;
    padding: 13px 14px;
    font-size: 16px;
  }
}

@media (max-width: 420px) {
  .top-code {
    width: 100%;
    grid-template-columns: 1fr;
    gap: 4px;
    padding: 12px 14px;
  }

  .podium-name {
    font-size: 18px;
  }
}
</style>
