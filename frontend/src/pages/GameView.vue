<template>
  <div class="page">
    <div v-if="store.roundData" class="container">
      <div class="player-header">
        <div class="track-meta">
          <span class="section-label">Now Playing</span>
          <h1>Round {{ store.roundData.round }}</h1>
          <p>Song {{ store.roundData.song_number }}/{{ store.roundData.songs_per_round }}</p>
        </div>

        <div class="track-stats">
          <div class="stat-box">
            <span>Lobby</span>
            <strong>{{ store.lobbyId }}</strong>
          </div>
          <div class="stat-box">
            <span>Time left</span>
            <strong>{{ remainingSeconds }}s</strong>
          </div>
        </div>
      </div>

      <div class="game-shell">
        <div class="visualizer-panel">
          <div class="wmp-display" aria-hidden="true">
            <div class="wmp-screen-glass"></div>
          </div>

          <div class="player-area">
            <div class="side-status">
              <span class="status-pill">{{ store.roundData.is_host_turn ? "HOST AUDIO" : "LISTEN MODE" }}</span>
              <span class="status-pill secondary">{{ showCountdown ? "COUNTDOWN" : "LIVE TRACK" }}</span>
            </div>

            <VinylPlayer
              :youtube-id="store.roundData.youtube_id"
              :start-time="store.roundData.start_time"
              :clip-duration="store.roundData.clip_duration"
              :clip-started-at="store.roundData.clip_started_at"
              :server-time-offset="store.serverTimeOffset"
              :play-audio="true"
              :countdown-active="showCountdown"
              :initially-muted="false"
            />

            <div v-if="showCountdown" class="countdown-box">
              <span class="countdown-label">Track starts in</span>
              <span class="countdown-number">{{ countdownValue }}</span>
            </div>
          </div>

          <div class="wmp-controls" aria-hidden="true">
            <div class="transport-buttons">
              <span class="transport prev"></span>
              <span class="transport play"></span>
              <span class="transport stop"></span>
              <span class="transport next"></span>
            </div>
            <div class="seek-track">
              <span></span>
            </div>
            <div class="volume-track">
              <span></span>
            </div>
          </div>
        </div>

        <div class="section answer-section">
          <RoundAnswerForm
            :key="`${store.roundData.round}-${store.roundData.song_number}`"
            :can-answer="canAnswer"
            :round-ends-at="store.roundData.round_ends_at"
            :year-options="store.roundData.year_options || []"
            @submit-answer="submitAnswer"
          />
        </div>

        <div v-if="showFinishFallback" class="fallback-box">
          <button type="button" class="finish-btn" @click="finishRoundNow">
            End track
          </button>
        </div>

        <p v-else-if="waitingForResults" class="waiting-note">
          Processing track results...
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import VinylPlayer from "../components/VinylPlayer.vue";
import RoundAnswerForm from "../components/RoundAnswerForm.vue";

const router = useRouter();
const route = useRoute();
const store = useGameStore();

const now = ref(Date.now() / 1000);
const lastPlayedCountdownNumber = ref(null);
const syncRequestedForRound = ref("");

let intervalId = null;
let audioContext = null;
let removeAudioUnlockListeners = null;
let submitRecoveryTimeout = null;

onMounted(async () => {
  intervalId = setInterval(() => {
    now.value = Date.now() / 1000 + store.serverTimeOffset;
  }, 250);

  setupAudioUnlock();
  window.addEventListener("visibilitychange", handleVisibilityRestore);
  window.addEventListener("focus", handleVisibilityRestore);

  if (!store.roundData && route.name !== "lobby") {
    const state = await store.fetchLobbyState();
    if (state?.phase !== "round") {
      await router.replace({ name: "lobby" });
    }
  }
});

onBeforeUnmount(() => {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }

  if (audioContext?.state !== "closed") {
    audioContext?.close?.();
  }

  removeAudioUnlockListeners?.();
  window.removeEventListener("visibilitychange", handleVisibilityRestore);
  window.removeEventListener("focus", handleVisibilityRestore);

  if (submitRecoveryTimeout) {
    clearTimeout(submitRecoveryTimeout);
    submitRecoveryTimeout = null;
  }
});

const clipStart = computed(() => store.roundData?.clip_started_at ?? 0);
const roundEnd = computed(() => store.roundData?.round_ends_at ?? 0);

const countdownRemaining = computed(() => {
  return Math.max(0, clipStart.value - now.value);
});

const countdownValue = computed(() => {
  if (!showCountdown.value) {
    return 0;
  }

  return Math.min(3, Math.max(1, Math.ceil(countdownRemaining.value) - 1));
});

const showCountdown = computed(() => {
  return countdownRemaining.value > 0;
});

const canAnswer = computed(() => {
  return now.value >= clipStart.value && now.value <= roundEnd.value;
});

const remainingSeconds = computed(() => {
  return Math.max(0, Math.ceil(roundEnd.value - now.value));
});

const waitingForResults = computed(() => {
  return remainingSeconds.value === 0;
});

const roundKey = computed(() => {
  if (!store.roundData) return "";
  return `${store.roundData.round}-${store.roundData.song_number}`;
});

const showFinishFallback = computed(() => {
  return (
    remainingSeconds.value === 0 &&
    store.phase === "round" &&
    store.roundData?.is_host_turn
  );
});

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

function setupAudioUnlock() {
  if (typeof window === "undefined") return;

  const unlockAudio = () => {
    const context = ensureAudioContext();
    if (!context) return;

    const buffer = context.createBuffer(1, 1, 22050);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);
    source.start(0);

    if (context.state === "running") {
      removeAudioUnlockListeners?.();
      removeAudioUnlockListeners = null;
    }
  };

  const events = ["pointerdown", "touchstart", "keydown"];

  events.forEach((eventName) => {
    window.addEventListener(eventName, unlockAudio, { passive: true });
  });

  removeAudioUnlockListeners = () => {
    events.forEach((eventName) => {
      window.removeEventListener(eventName, unlockAudio);
    });
  };
}

function playCountdownBeep(number) {
  const context = ensureAudioContext();
  if (!context) return;

  const oscillator = context.createOscillator();
  const gainNode = context.createGain();
  const nowTime = context.currentTime;

  const frequencyMap = {
    3: 620,
    2: 620,
    1: 920
  };

  oscillator.type = number === 1 ? "sawtooth" : "square";
  oscillator.frequency.setValueAtTime(frequencyMap[number] || 620, nowTime);

  gainNode.gain.setValueAtTime(0.0001, nowTime);
  gainNode.gain.exponentialRampToValueAtTime(0.16, nowTime + 0.02);
  gainNode.gain.exponentialRampToValueAtTime(0.0001, nowTime + (number === 1 ? 0.42 : 0.22));

  oscillator.connect(gainNode);
  gainNode.connect(context.destination);

  oscillator.start(nowTime);
  oscillator.stop(nowTime + (number === 1 ? 0.45 : 0.25));
}

async function requestResultSync() {
  if (!store.connected) {
    store.connect();
  }

  store.syncState();

  try {
    await store.fetchLobbyState();
  } catch (error) {
    console.error("Lobby state sync failed:", error);
  }
}

function handleVisibilityRestore() {
  if (document.visibilityState === "hidden") {
    return;
  }

  if (!store.connected) {
    store.connect();
  }

  requestResultSync();
}

function submitAnswer(payload) {
  store.submitAnswer(payload);

  const submittedRoundKey = roundKey.value;

  if (submitRecoveryTimeout) {
    clearTimeout(submitRecoveryTimeout);
  }

  submitRecoveryTimeout = setTimeout(() => {
    if (store.phase === "round" && roundKey.value === submittedRoundKey) {
      requestResultSync();
    }
  }, 1500);
}

function finishRoundNow() {
  store.finishSong();
}

watch(
  () => store.phase,
  async (phase) => {
    if ((phase === "leaderboard" || phase === "finished") && route.name !== "leaderboard") {
      await router.replace({ name: "leaderboard" });
    }
  },
  { flush: "post" }
);

watch(
  () => store.roundData?.clip_started_at,
  () => {
    lastPlayedCountdownNumber.value = null;
    syncRequestedForRound.value = "";
  }
);

watch(
  () => [waitingForResults.value, store.phase, roundKey.value, now.value],
  () => {
    if (!waitingForResults.value || store.phase !== "round" || !roundKey.value) {
      return;
    }

    if (syncRequestedForRound.value === roundKey.value) {
      return;
    }

    if (now.value < roundEnd.value + 2) {
      return;
    }

    syncRequestedForRound.value = roundKey.value;
    requestResultSync();
  }
);

watch(
  () => countdownValue.value,
  (value) => {
    if (!showCountdown.value) return;
    if (![1, 2, 3].includes(value)) return;
    if (lastPlayedCountdownNumber.value === value) return;

    playCountdownBeep(value);
    lastPlayedCountdownNumber.value = value;
  },
  { immediate: true }
);
</script>

<style scoped>
.page {
  min-height: 100%;
}

.container {
  width: 100%;
}

.player-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 14px;
}

.track-meta h1 {
  margin: 4px 0;
  color: var(--xp-text-bright);
  font-size: 28px;
  font-weight: 700;
}

.track-meta p,
.section-label {
  margin: 0;
  color: var(--xp-text-soft);
}

.section-label {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.track-stats {
  display: flex;
  gap: 12px;
  min-width: 0;
}

.stat-box {
  min-width: 126px;
  padding: 10px 12px;
  border: 1px solid rgba(164, 212, 255, 0.18);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(59, 108, 191, 0.35), rgba(16, 32, 66, 0.32));
}

.stat-box span {
  display: block;
  margin-bottom: 4px;
  color: var(--xp-text-soft);
  font-size: 11px;
  text-transform: uppercase;
}

.stat-box strong {
  color: var(--xp-text-bright);
  font-size: 18px;
}

.game-shell {
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.42);
  border-radius: 10px;
  background:
    linear-gradient(180deg, rgba(231, 241, 255, 0.42), rgba(73, 128, 206, 0.28) 18%, rgba(18, 54, 121, 0.72));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.72),
    0 14px 36px rgba(0, 30, 92, 0.32);
}

.visualizer-panel {
  position: relative;
  overflow: hidden;
  min-height: clamp(330px, 46vw, 390px);
  padding: 16px 16px 76px;
  border: 1px solid rgba(12, 35, 81, 0.88);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(187, 216, 252, 0.9), rgba(73, 126, 204, 0.82) 8%, rgba(14, 50, 121, 0.92) 17%, rgba(7, 18, 46, 0.98) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    inset 0 -1px 0 rgba(0, 0, 0, 0.42);
}

.wmp-display {
  position: absolute;
  inset: 16px 16px 76px;
  overflow: hidden;
  border: 1px solid rgba(198, 230, 255, 0.44);
  border-radius: 6px;
  background:
    linear-gradient(180deg, rgba(4, 13, 33, 0.4), rgba(0, 0, 0, 0.16)),
    radial-gradient(circle at 50% 54%, rgba(23, 142, 255, 0.26), transparent 26%),
    linear-gradient(180deg, #02060e 0%, #061024 46%, #010307 100%);
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.78),
    inset 0 0 34px rgba(47, 139, 255, 0.22),
    0 10px 26px rgba(0, 0, 0, 0.36);
}

.wmp-screen-glass {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.1), transparent 34%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.03) 0 1px, transparent 1px 4px);
  pointer-events: none;
  z-index: 2;
}

.visualizer-grid {
  position: absolute;
  inset: auto 26px 34px 26px;
  height: 150px;
  display: grid;
  grid-template-columns: repeat(36, 1fr);
  gap: 4px;
  align-items: end;
  opacity: 0.92;
}

.visualizer-grid span {
  min-height: 14px;
  border-radius: 3px 3px 0 0;
  background:
    linear-gradient(180deg, #fff675 0%, #67f7a9 30%, #21bfff 64%, #315eff 100%);
  animation: equalize 0.82s ease-in-out infinite alternate;
  box-shadow:
    0 0 9px rgba(45, 206, 255, 0.58),
    0 0 18px rgba(57, 93, 255, 0.32);
}

.visualizer-grid span:nth-child(3n) {
  animation-duration: 1.05s;
  background: linear-gradient(180deg, #ff7ad9 0%, #8dfbff 42%, #2b77ff 100%);
}

.visualizer-grid span:nth-child(4n) {
  animation-duration: 0.68s;
}

.visualizer-grid span:nth-child(5n) {
  animation-duration: 1.24s;
  background: linear-gradient(180deg, #fff59c 0%, #a2ff63 44%, #22a9ff 100%);
}

.scope-line {
  position: absolute;
  left: -8%;
  right: -8%;
  height: 92px;
  border-top: 2px solid rgba(109, 235, 255, 0.48);
  filter: drop-shadow(0 0 10px rgba(84, 220, 255, 0.75));
  opacity: 0.82;
}

.scope-line-one {
  bottom: 116px;
  border-radius: 48% 52% 42% 58%;
  transform: rotate(-3deg);
  animation: waveDrift 3.8s ease-in-out infinite alternate;
}

.scope-line-two {
  bottom: 94px;
  border-color: rgba(255, 119, 214, 0.42);
  border-radius: 42% 58% 52% 48%;
  transform: rotate(4deg);
  animation: waveDrift 3.2s ease-in-out infinite alternate-reverse;
}

.spectrum-floor {
  position: absolute;
  left: 20px;
  right: 20px;
  bottom: 18px;
  height: 30px;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(31, 201, 255, 0.36), transparent 68%);
  filter: blur(2px);
}

.player-area {
  position: relative;
  z-index: 3;
  min-height: 280px;
}

.side-status {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 8px;
}

.status-pill {
  padding: 6px 10px;
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(236, 247, 255, 0.22), rgba(30, 93, 184, 0.42));
  border: 1px solid rgba(185, 225, 255, 0.34);
  color: #e5f6ff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.32);
}

.status-pill.secondary {
  color: #ffe8a0;
}

.countdown-box {
  margin-top: 8px;
  text-align: center;
}

.countdown-label {
  display: block;
  color: var(--xp-text-soft);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.countdown-number {
  display: block;
  margin-top: 4px;
  color: #ffffff;
  font-size: 76px;
  font-weight: 700;
  text-shadow: 0 0 20px rgba(77, 176, 255, 0.6);
}

.wmp-controls {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 14px;
  z-index: 4;
  display: grid;
  grid-template-columns: auto minmax(120px, 1fr) 120px;
  gap: 14px;
  align-items: center;
  min-height: 46px;
  padding: 8px 12px;
  border: 1px solid rgba(4, 31, 85, 0.68);
  border-radius: 6px;
  background:
    linear-gradient(180deg, rgba(241, 248, 255, 0.86), rgba(155, 198, 248, 0.84) 44%, rgba(54, 113, 202, 0.88));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 -8px 24px rgba(0, 0, 0, 0.16);
}

.transport-buttons {
  display: flex;
  gap: 7px;
}

.transport {
  position: relative;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(24, 66, 137, 0.64);
  border-radius: 50%;
  background: radial-gradient(circle at 35% 24%, #ffffff 0 12%, #b7dcff 36%, #3d82de 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.8),
    0 1px 3px rgba(0, 26, 75, 0.3);
}

.transport::before,
.transport::after {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 8px;
  background: #113b87;
}

.transport.play::before {
  left: 11px;
  width: 0;
  height: 0;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  border-left: 9px solid #113b87;
  background: transparent;
}

.transport.stop::before {
  left: 9px;
  width: 10px;
}

.transport.prev::before,
.transport.next::before {
  width: 3px;
}

.transport.prev::before {
  left: 8px;
}

.transport.next::before {
  right: 8px;
}

.transport.prev::after,
.transport.next::after {
  top: 8px;
  width: 0;
  height: 0;
  border-top: 6px solid transparent;
  border-bottom: 6px solid transparent;
  background: transparent;
}

.transport.prev::after {
  left: 12px;
  border-right: 9px solid #113b87;
}

.transport.next::after {
  right: 12px;
  border-left: 9px solid #113b87;
}

.seek-track,
.volume-track {
  height: 10px;
  padding: 2px;
  border: 1px solid rgba(34, 76, 145, 0.6);
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(30, 60, 116, 0.35), rgba(255, 255, 255, 0.38));
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.22);
}

.seek-track span,
.volume-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1e65d0, #7bd4ff);
}

.seek-track span {
  width: 46%;
}

.volume-track span {
  width: 72%;
}

.answer-section {
  margin-top: 18px;
}

.waiting-note {
  margin: 18px 0 0;
  text-align: center;
  color: var(--xp-text-soft);
}

.fallback-box {
  margin-top: 18px;
  text-align: center;
}

.finish-btn {
  min-width: 170px;
  padding: 12px 20px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 10px;
  background: linear-gradient(180deg, #4d99ff, #2f5fb9);
  color: #fff;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.32);
}

@keyframes equalize {
  from {
    height: 18px;
  }

  to {
    height: 146px;
  }
}

@keyframes waveDrift {
  from {
    transform: translateX(-28px) rotate(-3deg) scaleY(0.82);
  }

  to {
    transform: translateX(28px) rotate(4deg) scaleY(1.08);
  }
}

@media (max-width: 900px) {
  .player-header {
    flex-direction: column;
  }

  .track-stats {
    flex-wrap: wrap;
  }

  .wmp-controls {
    grid-template-columns: 1fr;
  }

  .volume-track {
    display: none;
  }
}

@media (max-width: 560px) {
  .track-meta h1 {
    font-size: 23px;
  }

  .track-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }

  .stat-box {
    min-width: 0;
    padding: 9px 10px;
  }

  .stat-box strong {
    display: block;
    max-width: 100%;
    overflow-wrap: anywhere;
    font-size: 16px;
  }

  .game-shell {
    padding: 9px;
    border-radius: 8px;
  }

  .visualizer-panel {
    min-height: 318px;
    padding: 10px 10px 66px;
  }

  .wmp-display {
    inset: 10px 10px 66px;
  }

  .player-area {
    min-height: 236px;
  }

  .side-status {
    justify-content: center;
    flex-wrap: wrap;
  }

  .status-pill {
    font-size: 10px;
    letter-spacing: 0.04em;
  }

  .countdown-number {
    font-size: 56px;
  }

  .wmp-controls {
    left: 10px;
    right: 10px;
    bottom: 10px;
    gap: 8px;
    padding: 8px;
  }

  .transport-buttons {
    justify-content: center;
  }
}
</style>
