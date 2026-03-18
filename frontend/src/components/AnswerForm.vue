<template>
  <div class="card">
    <h3>Upiši odgovor</h3>
    <form @submit.prevent="submit">
      <input v-model="answer" type="text" placeholder="Naziv pjesme..." />
      <button type="submit">Pošalji odgovor</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";

const emit = defineEmits(["submit-answer"]);
const answer = ref("");

function submit() {
  if (!answer.value.trim()) return;
  emit("submit-answer", answer.value);
  answer.value = "";
}
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

form {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

input {
  flex: 1;
  padding: 12px;
  border-radius: 10px;
  border: none;
}

button {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
}
</style>