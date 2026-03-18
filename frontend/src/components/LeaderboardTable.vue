<template>
  <div class="card">
    <h3>Leaderboard</h3>
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Igrač</th>
          <th>Bodovi</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(player, index) in leaderboard" :key="player.name">
          <td>{{ index + 1 }}</td>
          <td>{{ player.name }}</td>
          <td>{{ player.score }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  leaderboard: {
    type: Array,
    default: () => []
  }
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

th, td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #374151;
}
</style>