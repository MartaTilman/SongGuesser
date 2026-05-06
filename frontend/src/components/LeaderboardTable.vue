<template>
  <div class="card">
    <h3 v-if="title">{{ title }}</h3>

    <div class="rows">
      <div v-for="(player, index) in sortedLeaderboard" :key="player.name" class="row">
        <div class="left">
          <span class="rank">{{ index + 1 }}.</span>
          <span class="avatar">{{ player.avatar || "🎵" }}</span>
          <span class="name">{{ player.name }}</span>
        </div>
        <div class="score">{{ player.score }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  leaderboard: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ""
  }
});

const sortedLeaderboard = computed(() => {
  return [...props.leaderboard].sort((a, b) => b.score - a.score);
});
</script>

<style scoped>
.card {
  padding: 14px 14px 18px;
  background: var(--panel);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-radius: 28px;
  box-shadow: var(--shadow-soft);
}

h3 {
  margin: 0 0 14px 8px;
  color: var(--text-blue);
  font-size: 18px;
  font-style: italic;
  font-weight: 700;
}

.rows {
  display: grid;
  gap: 12px;
}

.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 58px;
  padding: 10px 20px;
  background: rgba(214, 226, 255, 0.9);
  border-radius: 16px;
  color: var(--text-blue);
  font-size: 17px;
  font-style: italic;
  font-weight: 800;
}

.left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rank {
  min-width: 24px;
}

.avatar {
  font-size: 23px;
}

.score {
  color: var(--text-magenta);
  font-size: 18px;
}
</style>
