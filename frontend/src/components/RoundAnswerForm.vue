<template>
  <div class="card">
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

    <button
      class="submit-btn"
      type="button"
      :disabled="submitted || !canAnswer"
      @click="submit"
    >
      {{ submitted ? "Answer submitted" : "Submit answer" }}
    </button>
  </div>
</template>

<script setup>
import { ref } from "vue";

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

function submit() {
  if (submitted.value) return;

  emit("submit-answer", {
    title_answer: titleAnswer.value,
    artist_answer: artistAnswer.value,
    year_answer: yearAnswer.value
  });

  submitted.value = true;
}
</script>

<style scoped>
.card {
  padding: 0;
}

.answers-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: 30px;
  align-items: start;
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
  margin: 0 0 16px;
  text-align: center;
  color: var(--xp-text-soft);
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.year-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px 16px;
}

.year-grid button,
.submit-btn {
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

.submit-btn {
  display: block;
  min-width: 192px;
  margin: 18px auto 0;
  padding: 14px 22px;
  background: linear-gradient(180deg, #5db3ff 0%, #315fb8 100%);
  color: white;
  font-size: 15px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  box-shadow: 0 10px 22px rgba(30, 82, 170, 0.28);
}

.year-grid button:disabled,
.submit-btn:disabled,
input:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

@media (max-width: 720px) {
  .answers-layout {
    grid-template-columns: 1fr;
    gap: 18px;
  }
}
</style>
