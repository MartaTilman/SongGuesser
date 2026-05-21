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
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(218, 233, 255, 0.96));
  border: 1px solid rgba(255, 255, 255, 0.78);
  border-radius: 16px;
  color: #0b2563;
  font-size: 17px;
  font-style: italic;
  font-weight: 800;
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.55);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 4px 12px rgba(44, 84, 150, 0.12);
}

.left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.rank {
  min-width: 24px;
}

.avatar {
  font-size: 23px;
}

.score {
  flex: 0 0 auto;
  color: #174d9d;
  font-size: 18px;
}

.name {
  min-width: 0;
  overflow-wrap: anywhere;
}

@media (max-width: 520px) {
  .card {
    padding: 12px 10px 14px;
    border-radius: 18px;
  }

  .row {
    min-height: 52px;
    padding: 10px 12px;
    gap: 10px;
    font-size: 15px;
  }

  .left {
    gap: 7px;
  }

  .rank {
    min-width: 20px;
  }

  .score {
    font-size: 16px;
  }
}
</style>
