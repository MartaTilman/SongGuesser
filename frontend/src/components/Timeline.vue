<template>
  <div class="card">
    <h3>Status igre</h3>
    <p>{{ status }}</p>
  </div>
</template>

<script setup>
defineProps({
  status: String
});
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}
</style>