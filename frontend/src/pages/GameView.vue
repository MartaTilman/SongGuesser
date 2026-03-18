<template>
  <div class="page">
    <div class="container" v-if="store.roundData">
      <h1>Runda {{ store.roundData.round }}</h1>

      <div class="grid">
        <div class="card">
          <p>Pjesma: {{ store.roundData.song_number }} / {{ store.roundData.songs_per_round }}</p>
          <p>Dekada: {{ store.roundData.decade }}</p>
          <p>Vrijeme: {{ remainingSeconds }} s</p>
          <p>Faza: {{ phaseLabel }}</p>
        </div>

        <VinylPlayer
  :youtube-id="store.roundData.youtube_id"
  :start-time="store.roundData.start_time"
  :clip-duration="store.roundData.clip_duration"
  :clip-started-at="store.roundData.clip_started_at"
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
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import VinylPlayer from "../components/VinylPlayer.vue";
import RoundAnswerForm from "../components/RoundAnswerForm.vue";

const router = useRouter();
const store = useGameStore();

const now = ref(Date.now() / 1000);
let interval = null;

onMounted(() => {
  interval = setInterval(() => {
    now.value = Date.now() / 1000;
  }, 250);
});

onBeforeUnmount(() => {
  if (interval) clearInterval(interval);
});

const clipStart = computed(() => store.roundData?.clip_started_at || 0);
const clipEnd = computed(() => clipStart.value + (store.roundData?.clip_duration || 0));
const roundEnd = computed(() => store.roundData?.round_ends_at || 0);

const isClipPlaying = computed(() => {
  return now.value >= clipStart.value && now.value <= clipEnd.value;
});

const canAnswer = computed(() => {
  return now.value >= clipStart.value && now.value <= roundEnd.value;
});

const phaseLabel = computed(() => {
  if (now.value <= clipEnd.value) return "slušanje + odgovaranje";
  if (now.value <= roundEnd.value) return "zadnjih 5 sekundi za odgovore";
  return "čekanje rezultata";
});

const remainingSeconds = computed(() => {
  return Math.max(0, Math.ceil(roundEnd.value - now.value));
});

function submitAnswer(payload) {
  store.submitAnswer(payload);
}

watch(
  () => store.phase,
  (phase) => {
    if (phase === "leaderboard" || phase === "finished") {
      router.push("/leaderboard");
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
</style>