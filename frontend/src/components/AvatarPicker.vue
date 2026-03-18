<template>
  <div class="avatar-picker">
    <label>Odaberi avatar</label>
    <div class="avatars">
      <button
        v-for="avatar in avatars"
        :key="avatar"
        :class="{ active: modelValue === avatar }"
        @click="$emit('update:modelValue', avatar)"
      >
        {{ avatar }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: String
});

defineEmits(["update:modelValue"]);

const avatars = ["🎵", "🎤", "🎸", "🥁", "🎧", "🔥"];
</script>

<style scoped>
.avatar-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.avatars {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

button {
  padding: 10px 14px;
  border: none;
  border-radius: 10px;
  background: #1f2937;
  color: white;
  font-size: 20px;
}

button.active {
  background: #2563eb;
}
</style>