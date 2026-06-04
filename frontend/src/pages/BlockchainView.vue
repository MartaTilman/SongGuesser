<template>
  <div class="page">
    <div class="container">
      <h1>Blockchain zapis</h1>
      <p>
        Status lanca:
        <strong :class="store.blockchainValid ? 'valid' : 'invalid'">
          {{ store.blockchainValid ? "VALIDAN" : "NEVALIDAN" }}
        </strong>
      </p>
      <p v-if="store.blockchainConsensus">
        Consensus: <strong>{{ formatConsensus(store.blockchainConsensus) }}</strong>
        <span v-if="store.blockchainDifficulty">
          | Difficulty: <strong>{{ store.blockchainDifficulty }}</strong>
        </span>
      </p>

      <div class="actions">
        <button type="button" @click="refresh">Osvježi</button>
        <button type="button" @click="goBack">Natrag</button>
      </div>

      <div class="blocks">
        <div class="block-card" v-for="block in store.blockchain" :key="block.index">
          <h3>Blok #{{ block.index }}</h3>
          <p><strong>Hash:</strong> {{ block.hash }}</p>
          <p><strong>Previous:</strong> {{ block.previous_hash }}</p>
          <p v-if="block.nonce !== undefined"><strong>Nonce:</strong> {{ block.nonce }}</p>
          <p v-if="block.difficulty !== undefined"><strong>Difficulty:</strong> {{ block.difficulty }}</p>
          <p><strong>Timestamp:</strong> {{ formatTime(block.timestamp) }}</p>

          <pre>{{ JSON.stringify(block.data, null, 2) }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";

const router = useRouter();
const store = useGameStore();

onMounted(async () => {
  await store.fetchBlockchain();
});

async function refresh() {
  await store.fetchBlockchain();
}

function goBack() {
  if (store.phase === "round") {
    router.push("/game");
    return;
  }

  if (store.phase === "leaderboard" || store.phase === "finished") {
    router.push("/leaderboard");
    return;
  }

  router.push("/lobby");
}

function formatTime(timestamp) {
  return new Date(timestamp * 1000).toLocaleString();
}

function formatConsensus(consensus) {
  return String(consensus || "").replaceAll("_", " ").toUpperCase();
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  padding: 30px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
}

.actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

button {
  padding: 12px 18px;
  border: none;
  border-radius: 10px;
  background: #2563eb;
  color: white;
}

.blocks {
  display: grid;
  gap: 16px;
}

.block-card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  background: #111827;
  padding: 12px;
  border-radius: 10px;
}

.valid {
  color: #4ade80;
}

.invalid {
  color: #f87171;
}
</style>
