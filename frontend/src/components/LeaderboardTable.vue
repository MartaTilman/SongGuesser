<template>
  <div class="card">
    <h3>{{ title }}</h3>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Igrač</th>
          <th>Bodovi</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(player, index) in sortedLeaderboard" :key="player.name">
          <td>{{ index + 1 }}</td>
          <td class="player-cell">
            <span class="avatar">{{ player.avatar || "🎵" }}</span>
            <span>{{ player.name }}</span>
          </td>
          <td>{{ player.score }}</td>
        </tr>
      </tbody>
    </table>
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
    default: "Leaderboard"
  }
});

const sortedLeaderboard = computed(() => {
  return [...props.leaderboard].sort((a, b) => b.score - a.score);
});
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #374151;
}

.player-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.avatar {
  font-size: 20px;
}
</style>
