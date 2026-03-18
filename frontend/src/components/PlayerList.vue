<template>
  <div class="card">
    <h3>Igrači u lobbyju</h3>
    <ul class="players">
      <li v-for="player in players" :key="player.name">
        <span class="avatar">{{ player.avatar }}</span>
        <span>{{ player.name }}</span>
        <span v-if="player.name === host" class="host-badge">HOST</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
defineProps({
  players: {
    type: Array,
    default: () => []
  },
  host: {
    type: String,
    default: ""
  }
});
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

.players {
  list-style: none;
  padding: 0;
  margin: 0;
}

.players li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid #374151;
}

.avatar {
  font-size: 24px;
}

.host-badge {
  margin-left: auto;
  background: #2563eb;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
}
</style>