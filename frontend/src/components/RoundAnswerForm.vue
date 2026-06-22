<template>
  <div class="card">
    <div class="status-bar">
      <span v-if="submitted" class="status-badge submitted">✓ Answer submitted</span>
      <span v-else-if="canAnswer" class="status-badge active">Answer now!</span>
      <span v-else class="status-badge waiting">Waiting for song to start...</span>
    </div>

    <div class="answers-layout">
      <div class="left-side">
        <div class="field">
          <input
            v-model="titleAnswer"
            :disabled="submitted || !canAnswer"
            placeholder="Song title"
          />
        </div>

        <div class="field">
          <input
            v-model="artistAnswer"
            :disabled="submitted || !canAnswer"
            placeholder="Artist"
          />
        </div>

        <button
          v-if="!submitted"
          type="button"
          class="submit-btn"
          :disabled="!canAnswer"
          @click="submit"
        >
          Submit answer
        </button>
      </div>

      <div class="right-side">
        <p class="year-title">What year was the song released?</p>
        <div class="year-grid">
          <button
            v-for="year in yearOptions"
            :key="year"
            type="button"
            :disabled="submitted || !canAnswer"
            :class="{ selected: yearAnswer === year }"
            @click="yearAnswer = year"
          >
            {{ year }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from "vue";

const props = defineProps({
  canAnswer: Boolean,
  roundEndsAt: {
    type: Number,
    default: 0
  },
  yearOptions: {
    type: Array,
    default: () => []
  }
});

const emit = defineEmits(["submit-answer"]);

const titleAnswer = ref("");
const artistAnswer = ref("");
const yearAnswer = ref(null);
const submitted = ref(false);
const answerWindowOpened = ref(false);

function submit() {
  if (submitted.value) return;

  emit("submit-answer", {
    title_answer: titleAnswer.value,
    artist_answer: artistAnswer.value,
    year_answer: yearAnswer.value
  });

  submitted.value = true;
}

// Set initial state on mount (don't auto-submit here — no prev value to compare against)
onMounted(() => {
  if (props.canAnswer) {
    answerWindowOpened.value = true;
  }
});

// Only auto-submit when canAnswer GENUINELY transitions true → false
watch(
  () => props.canAnswer,
  (canAnswer, prevCanAnswer) => {
    if (canAnswer) {
      answerWindowOpened.value = true;
      return;
    }

    // prevCanAnswer is undefined on first run if immediate is not set,
    // so this only fires on real transitions
    if (prevCanAnswer && answerWindowOpened.value) {
      submit();
    }
  }
);

watch(
  () => props.roundEndsAt,
  () => {
    submitted.value = false;
    answerWindowOpened.value = false;
    titleAnswer.value = "";
    artistAnswer.value = "";
    yearAnswer.value = null;
  }
);
</script>

<style scoped>
.card {
  padding: 0;
}

.status-bar {
  margin-bottom: 10px;
}

.status-badge {
  display: inline-block;
  padding: 5px 12px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.status-badge.waiting {
  background: rgba(100, 120, 180, 0.28);
  color: rgba(177, 208, 255, 0.78);
  border: 1px solid rgba(165, 214, 255, 0.15);
}

.status-badge.active {
  background: rgba(37, 99, 235, 0.45);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.5);
  animation: pulse 1.4s ease-in-out infinite;
}

.status-badge.submitted {
  background: rgba(22, 163, 74, 0.3);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.35);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.submit-btn {
  margin-top: 16px;
  width: 100%;
  height: 48px;
  border: 1px solid rgba(165, 214, 255, 0.3);
  border-radius: 10px;
  background: linear-gradient(180deg, #3b82f6, #1d4ed8);
  color: white;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.15);
  transition: opacity 0.15s;
}

.submit-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.answers-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 30px;
  align-items: start;
  margin-top: 32px;
}

.field + .field {
  margin-top: 16px;
}

input {
  width: 100%;
  height: 56px;
  padding: 0 20px;
  border: 1px solid rgba(165, 214, 255, 0.2);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(59, 97, 171, 0.35), rgba(17, 31, 66, 0.55));
  color: var(--xp-text-bright);
  font-size: 17px;
  font-weight: 700;
  outline: none;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

input::placeholder {
  color: rgba(177, 208, 255, 0.78);
}

.year-title {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 12px);
  margin: 0;
  text-align: center;
  color: var(--xp-text-soft);
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.right-side {
  position: relative;
}

.year-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px 16px;
}

.year-grid button {
  border: 1px solid rgba(165, 214, 255, 0.2);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(59, 97, 171, 0.35), rgba(17, 31, 66, 0.55));
  color: var(--xp-text-bright);
  font-size: 16px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

.year-grid button {
  min-height: 52px;
}

.year-grid button.selected {
  background: linear-gradient(180deg, #5db3ff 0%, #315fb8 100%);
  color: white;
}

.year-grid button:disabled,
input:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .answers-layout {
    grid-template-columns: 1fr;
    gap: 42px;
    margin-top: 18px;
  }
}

@media (max-width: 520px) {
  input {
    height: 50px;
    padding-inline: 14px;
    font-size: 15px;
  }

  .year-title {
    position: static;
    margin: 0 0 10px;
    font-size: 12px;
    letter-spacing: 0.04em;
  }

  .answers-layout {
    gap: 18px;
  }

  .year-grid {
    gap: 10px;
  }

  .year-grid button {
    min-height: 46px;
  }
}
</style>
