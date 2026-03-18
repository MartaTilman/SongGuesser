<template>
  <div class="card">
    <h3>Odgovori</h3>

    <div class="field">
      <label>Naziv pjesme</label>
      <input
        v-model="titleAnswer"
        :disabled="submitted || !canAnswer"
        placeholder="Upiši naziv pjesme"
      />
    </div>

    <div class="field">
      <label>Izvođač</label>
      <input
        v-model="artistAnswer"
        :disabled="submitted || !canAnswer"
        placeholder="Upiši izvođača"
      />
    </div>

    <div class="field">
      <label>Godina</label>
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

    <button
      class="submit-btn"
      :disabled="submitted || !canAnswer"
      @click="submit"
    >
      {{ submitted ? "Odgovori poslani" : "Pošalji odgovore" }}
    </button>
  </div>
</template>

<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  canAnswer: Boolean,
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

watch(
  () => props.canAnswer,
  (newValue, oldValue) => {
    if (oldValue === true && newValue === false && !submitted.value) {
      submit();
    }
  }
);
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

.field {
  margin-bottom: 16px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #e5e7eb;
}

input {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: #f9fafb;
}

.year-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.year-grid button,
.submit-btn {
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: #374151;
  color: white;
  transition: 0.2s ease;
}

.year-grid button.selected {
  background: #2563eb;
}

.submit-btn {
  width: 100%;
  background: #16a34a;
  margin-top: 8px;
}

.year-grid button:disabled,
.submit-btn:disabled,
input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
</style>