<template>
  <div class="avatar-picker">
    <div class="avatars">
      <button
        v-for="avatar in avatars"
        :key="avatar"
        type="button"
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

const avatars = ["🎻", "🎸", "🎷", "🥁", "🎺"];
</script>

<style scoped>
.avatar-picker {
  margin-bottom: 10px;
}

.avatars {
  display: flex;
  justify-content: center;
  gap: 10px;
}

button {
  width: 46px;
  height: 36px;
  border: 0;
  border-radius: 12px;
  background: rgba(245, 248, 255, 0.88);
  color: var(--text-blue);
  font-size: 20px;
  box-shadow: 0 6px 14px rgba(125, 163, 255, 0.14);
}

button.active {
  background: #84a8ff;
  color: white;
}
</style>
