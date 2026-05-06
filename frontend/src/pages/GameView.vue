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
          <div class="visualizer-grid" aria-hidden="true">
            <span v-for="bar in 22" :key="bar" :style="{ animationDelay: `${bar * 0.08}s` }"></span>
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
              :play-audio="true"
              :countdown-active="showCountdown"
              :initially-muted="!store.roundData.is_host_turn"
            />

            <div v-if="showCountdown" class="countdown-box">
              <span class="countdown-label">Track starts in</span>
              <span class="countdown-number">{{ countdownValue }}</span>
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

let intervalId = null;
let audioContext = null;
let removeAudioUnlockListeners = null;

onMounted(async () => {
  intervalId = setInterval(() => {
    now.value = Date.now() / 1000;
  }, 250);

  setupAudioUnlock();

  if (!store.roundData && route.name !== "lobby") {
    await router.replace({ name: "lobby" });
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

function submitAnswer(payload) {
  store.submitAnswer(payload);
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
  padding: 18px;
  border: 1px solid rgba(177, 221, 255, 0.16);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(11, 24, 56, 0.9), rgba(9, 17, 40, 0.96));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.visualizer-panel {
  position: relative;
  overflow: hidden;
  min-height: 328px;
  padding: 24px 20px;
  border: 1px solid rgba(150, 212, 255, 0.18);
  border-radius: 12px;
  background:
    radial-gradient(circle at 50% 20%, rgba(86, 123, 255, 0.22), transparent 22%),
    linear-gradient(180deg, rgba(14, 32, 70, 0.96), rgba(6, 15, 38, 0.94));
}

.visualizer-grid {
  position: absolute;
  inset: auto 20px 18px 20px;
  height: 84px;
  display: grid;
  grid-template-columns: repeat(22, 1fr);
  gap: 6px;
  align-items: end;
  opacity: 0.7;
}

.visualizer-grid span {
  border-radius: 999px 999px 2px 2px;
  background:
    linear-gradient(180deg, #d44cff 0%, #45c8ff 55%, #65f0b5 100%);
  animation: equalize 1.2s ease-in-out infinite alternate;
  box-shadow: 0 0 14px rgba(86, 214, 255, 0.35);
}

.player-area {
  position: relative;
  z-index: 1;
}

.side-status {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-bottom: 8px;
}

.status-pill {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(82, 124, 201, 0.28);
  border: 1px solid rgba(156, 219, 255, 0.16);
  color: #bfe4ff;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
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
    height: 12px;
  }

  to {
    height: 82px;
  }
}

@media (max-width: 900px) {
  .player-header {
    flex-direction: column;
  }

  .track-stats {
    flex-wrap: wrap;
  }
}
</style>
