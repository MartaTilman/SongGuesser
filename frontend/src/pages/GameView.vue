<template>
  <div class="page">
    <div v-if="store.roundData" class="container">
      <h1>Runda {{ store.roundData.round }}</h1>

      <div class="grid">
        <div class="card">
          <p>Pjesma: {{ store.roundData.song_number }} / {{ store.roundData.songs_per_round }}</p>
          <p>Vrijeme: {{ remainingSeconds }} s</p>
          <p>Faza: {{ phaseLabel }}</p>

          <p v-if="store.roundData.is_host_turn" class="host-note">
            Ti si host, zvuk ide samo kod tebe.
          </p>
          <p v-else class="listener-note">
            Slušaj pjesmu i upiši odgovore ovdje.
          </p>

          <div v-if="showCountdown" class="countdown-box">
            <span class="countdown-label">Runda počinje za</span>
            <strong class="countdown-number">{{ countdownValue }}</strong>
          </div>

          <div v-if="showFinishFallback" class="fallback-box">
            <button type="button" class="finish-btn" @click="finishRoundNow">
              Završi rundu
            </button>
          </div>

          <p v-else-if="waitingForResults" class="waiting-note">
            Čekanje rezultata...
          </p>
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
      </div>

      <div class="section">
        <RoundAnswerForm
          :key="`${store.roundData.round}-${store.roundData.song_number}`"
          :can-answer="canAnswer"
          :round-ends-at="store.roundData.round_ends_at"
          :year-options="store.roundData.year_options || []"
          @submit-answer="submitAnswer"
        />
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
const clipEnd = computed(() => clipStart.value + (store.roundData?.clip_duration ?? 0));
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

const phaseLabel = computed(() => {
  if (showCountdown.value) return "odbrojavanje";
  if (now.value <= clipEnd.value) return "slušanje + odgovaranje";
  if (now.value <= roundEnd.value) return "zadnjih sekundi za odgovore";
  return "čekanje rezultata";
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
  min-height: 100vh;
  padding: 30px;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
}

.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.section {
  margin-top: 20px;
}

.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

.host-note {
  margin-top: 10px;
  color: #86efac;
}

.listener-note {
  margin-top: 10px;
  color: #d1d5db;
}

.countdown-box {
  margin-top: 18px;
  background: #111827;
  border: 1px solid #374151;
  border-radius: 14px;
  padding: 18px;
  text-align: center;
}

.countdown-label {
  display: block;
  color: #9ca3af;
  margin-bottom: 8px;
}

.countdown-number {
  display: block;
  font-size: 56px;
  line-height: 1;
  color: #facc15;
}

.waiting-note {
  margin-top: 16px;
  color: #facc15;
  font-weight: 600;
}

.fallback-box {
  margin-top: 16px;
}

.finish-btn {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #dc2626;
  color: white;
  font-weight: 700;
  cursor: pointer;
}
</style>
