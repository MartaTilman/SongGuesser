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
          :play-audio="store.roundData.is_host_turn"
          :countdown-active="showCountdown"
        />
      </div>

      <div class="section">
        <RoundAnswerForm
          :key="`${store.roundData.round}-${store.roundData.song_number}`"
          :can-answer="canAnswer"
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
let intervalId = null;

onMounted(async () => {
  intervalId = setInterval(() => {
    now.value = Date.now() / 1000;
  }, 250);

  if (!store.roundData && route.name !== "lobby") {
    await router.replace({ name: "lobby" });
  }
});

onBeforeUnmount(() => {
  if (intervalId) {
    clearInterval(intervalId);
    intervalId = null;
  }
});

const clipStart = computed(() => store.roundData?.clip_started_at ?? 0);
const clipEnd = computed(() => clipStart.value + (store.roundData?.clip_duration ?? 0));
const roundEnd = computed(() => store.roundData?.round_ends_at ?? 0);

const countdownRemaining = computed(() => {
  return Math.max(0, clipStart.value - now.value);
});

const countdownValue = computed(() => {
  return Math.max(1, Math.ceil(countdownRemaining.value));
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
