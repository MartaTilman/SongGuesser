<template>
  <div class="card">
    <h3>Info o rundi</h3>
    <p>Runda: {{ round }}</p>
    <p>Pjesma: {{ songNumber }} / {{ songsPerRound }}</p>
    <p>Dekada: {{ decade || "-" }}</p>
    <p v-if="duration">Trajanje isječka: {{ duration }} s</p>
  </div>
</template>

<script setup>
defineProps({
  round: Number,
  songNumber: Number,
  songsPerRound: Number,
  decade: String,
  duration: Number
});
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}
</style>