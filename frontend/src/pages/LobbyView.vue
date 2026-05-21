<template>
  <div class="page">
    <div class="container">
      <div class="lobby-header">
        <div class="lobby-code-card">
          <span class="code-label">Lobby ID</span>
          <div class="code-copy-row">
            <strong class="code-value">{{ store.lobbyId }}</strong>
            <button
              class="copy-btn"
              type="button"
              aria-label="Copy lobby code"
              title="Copy lobby code"
              @click="copyLobbyCode"
            >
              <img src="/icons8-copy-30.png" alt="" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <div class="content-grid">
        <PlayerList :players="store.players" :host="store.host" />

        <div class="side-panel">
          <div class="task-card">
            <h3>Lobby status</h3>
            <p>{{ store.isHost ? "You are the host of this session." : "Host is preparing the next game." }}</p>
          </div>

          <div class="task-card controls-card">
            <button v-if="store.isHost" type="button" @click="store.startRound()">
              Start the game
            </button>
            <p v-else class="waiting-text">Waiting for host to start the game...</p>

            <p v-if="copyMessage" class="copy-message">{{ copyMessage }}</p>
          </div>
        </div>
      </div>

      <div v-if="store.error" class="error-box">
        {{ store.error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import PlayerList from "../components/PlayerList.vue";

const router = useRouter();
const route = useRoute();
const store = useGameStore();
const copyMessage = ref("");

onMounted(async () => {
  if (!store.lobbyId || !store.playerName) {
    await router.replace({ name: "home" });
    return;
  }

  try {
    await store.fetchLobbyInfo();
    store.connect();
  } catch (error) {
    console.error("Lobby info fetch failed:", error);
    store.error = "Ne mogu dohvatiti informacije o lobbyju.";
  }
});

watch(
  () => store.phase,
  async (phase) => {
    if (phase === "round" && route.name !== "game") {
      await router.replace({ name: "game" });
    }
  },
  { flush: "post" }
);

async function copyLobbyCode() {
  try {
    await copyText(store.lobbyId);
    copyMessage.value = "Code copied.";
  } catch (error) {
    copyMessage.value = "Copy failed.";
  }
}

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch (error) {
      // Some browsers expose the Clipboard API but block it without a permission grant.
    }
  }

  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.setAttribute("readonly", "");
  textArea.style.position = "fixed";
  textArea.style.top = "-1000px";
  textArea.style.opacity = "0";
  document.body.appendChild(textArea);
  textArea.select();

  try {
    const copied = document.execCommand("copy");
    if (!copied) {
      throw new Error("Copy command failed.");
    }
  } finally {
    document.body.removeChild(textArea);
  }
}
</script>

<style scoped>
.page {
  min-height: 100%;
}

.container {
  color: #123f8d;
}

.lobby-header {
  display: flex;
  justify-content: flex-start;
  gap: 14px;
  align-items: center;
  margin-bottom: 18px;
}

.lobby-code-card {
  display: inline-flex;
  max-width: 100%;
  gap: 14px;
  align-items: center;
  padding: 10px 14px;
  border: 1px solid #8daee0;
  border-radius: 9px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(216, 231, 255, 0.94));
}

.code-copy-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.code-label {
  font-size: 12px;
  text-transform: uppercase;
  color: #4c6cae;
}

.code-value {
  display: block;
  max-width: 100%;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.05em;
  overflow-wrap: anywhere;
}

.controls-card button {
  padding: 10px 16px;
  border: 1px solid #2959b7;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #cfe1fb 15%, #84b5ff 52%, #5f8fed 100%);
  color: #123f92;
  font-size: 15px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.copy-btn {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid #8daee0;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.66);
  cursor: pointer;
}

.copy-btn:hover {
  background: rgba(255, 255, 255, 0.9);
}

.copy-btn img {
  width: 18px;
  height: 18px;
  object-fit: contain;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(280px, 0.8fr);
  gap: 18px;
}

.side-panel {
  display: grid;
  gap: 14px;
}

.task-card {
  padding: 16px;
  border: 1px solid #97b4e0;
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(224, 235, 255, 0.88));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.task-card h3 {
  margin: 0 0 8px;
  color: #18458f;
  font-size: 16px;
}

.task-card p {
  margin: 0;
  line-height: 1.4;
}

.controls-card {
  display: flex;
  min-height: 180px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 12px;
}

.waiting-text {
  text-align: center;
}

.copy-message {
  color: #2f5db3;
  font-weight: 700;
}

.error-box {
  margin-top: 16px;
  padding: 14px 16px;
  border: 1px solid #c97e7e;
  border-radius: 8px;
  background: #ffe1e1;
  color: #aa2e2e;
  font-weight: 700;
}

@media (max-width: 900px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .lobby-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 540px) {
  .lobby-code-card {
    width: 100%;
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .code-copy-row {
    width: 100%;
    justify-content: space-between;
  }

  .controls-card {
    min-height: 132px;
  }

  .controls-card button {
    width: 100%;
  }
}
</style>
