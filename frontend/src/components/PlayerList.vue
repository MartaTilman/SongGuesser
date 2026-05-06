<template>
  <div class="player-card">
    <h3>Players</h3>

    <div class="player-list">
      <div v-for="player in players" :key="player.name" class="player-row">
        <span class="avatar">{{ player.avatar || "🎵" }}</span>
        <span class="name">{{ player.name }}</span>
        <span v-if="player.name === host" class="host-badge">HOST</span>
      </div>
    </div>
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
.player-card {
  padding: 18px 14px 18px;
  background: var(--panel);
  backdrop-filter: blur(20px);
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-radius: 28px;
  box-shadow: var(--shadow-soft);
}

h3 {
  margin: 0 0 16px 10px;
  color: var(--text-blue);
  font-size: 18px;
  font-style: italic;
  font-weight: 700;
}

.player-list {
  display: grid;
  gap: 6px;
}

.player-row {
  display: grid;
  grid-template-columns: 48px 1fr auto;
  align-items: center;
  min-height: 58px;
  padding: 10px 18px 10px 14px;
  background: rgba(214, 226, 255, 0.88);
  border-radius: 16px;
  color: var(--text-blue);
  font-size: 17px;
  font-style: italic;
  font-weight: 800;
}

.avatar {
  font-size: 24px;
}

.host-badge {
  padding: 6px 14px;
  border-radius: 999px;
  background: var(--badge-yellow);
  color: #ff8e22;
}

@media (max-width: 540px) {
  .player-row {
    grid-template-columns: 40px 1fr auto;
    padding-inline: 10px 12px;
    font-size: 15px;
  }

  .host-badge {
    padding-inline: 10px;
    font-size: 13px;
  }
}
</style>
