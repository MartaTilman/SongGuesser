<template>
  <div class="desktop-page">
    <div class="bliss-bg" aria-hidden="true">
      <div class="sky-glow"></div>
      <div class="hill hill-back"></div>
      <div class="hill hill-front"></div>
    </div>

    <button
      type="button"
      class="desktop-icon"
      :class="{ zooming: zooming }"
      @click="openWindow"
    >
      <span class="icon-art"></span>
      <span class="icon-label">Song Guesser</span>
    </button>

    <transition name="xp-pop">
      <div v-if="windowOpen" class="login-window">
        <div class="login-titlebar">
          <div class="login-title-left">
            <span class="mini-icon"></span>
            <strong>SongGuesser.exe</strong>
          </div>

          <button type="button" class="close-btn" @click="closeWindow">×</button>
        </div>

        <div class="login-toolbar">
          <span>File</span>
          <span>Edit</span>
          <span>Favorites</span>
          <span>Help</span>
        </div>

        <div class="login-body">
          <p class="subtitle">Open multiplayer session</p>

          <AvatarPicker v-model="avatar" />

          <input v-model="playerName" type="text" placeholder="Name" />

          <input
            v-if="mode === 'join'"
            v-model="lobbyId"
            type="text"
            placeholder="Lobby ID"
          />

          <div v-else class="generated-box">
            Lobby ID will be generated automatically
          </div>

          <button type="button" class="xp-btn main-btn" :disabled="loading" @click="joinGame">
            {{ loading && mode === "join" ? "Loading..." : "Get in the game" }}
          </button>

          <p class="or-label">or</p>

          <button type="button" class="xp-btn" :disabled="loading" @click="createGame">
            {{ loading && mode === "create" ? "Loading..." : "Make lobby" }}
          </button>

          <p v-if="error" class="error">{{ error }}</p>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useGameStore } from "../stores/gameStore";
import AvatarPicker from "../components/AvatarPicker.vue";

const router = useRouter();
const store = useGameStore();

const mode = ref("join");
const playerName = ref("");
const lobbyId = ref("");
const avatar = ref("🎵");
const error = ref("");
const loading = ref(false);
const windowOpen = ref(false);
const zooming = ref(false);

async function runSubmit(selectedMode) {
  error.value = "";
  mode.value = selectedMode;

  if (!playerName.value.trim()) {
    error.value = "Unesi ime igraca.";
    return;
  }

  if (selectedMode === "join" && !lobbyId.value.trim()) {
    error.value = "Unesi lobby kod.";
    return;
  }

  loading.value = true;

  try {
    if (selectedMode === "create") {
      await store.createLobby(playerName.value.trim(), avatar.value);
    } else {
      await store.joinExistingLobby(playerName.value.trim(), lobbyId.value.trim(), avatar.value);
    }

    store.connect();
    await router.push("/lobby");
  } catch (err) {
    error.value =
      err?.response?.data?.detail ||
      err?.message ||
      "Neuspjesno spajanje na lobby.";
  } finally {
    loading.value = false;
  }
}

function joinGame() {
  runSubmit("join");
}

function createGame() {
  runSubmit("create");
}

function openWindow() {
  if (windowOpen.value || zooming.value) return;

  zooming.value = true;

  setTimeout(() => {
    windowOpen.value = true;
    zooming.value = false;
  }, 520);
}

function closeWindow() {
  windowOpen.value = false;
}
</script>

<style scoped>
.desktop-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.bliss-bg {
  position: fixed;
  inset: 0;
  background:
    url("/pozadina-livada.jpg") center center / cover no-repeat;
}

.sky-glow {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(0, 37, 91, 0.1));
}

.desktop-icon {
  position: absolute;
  top: 28px;
  left: 26px;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: 98px;
  padding: 8px 4px;
  border: 0;
  background: transparent;
  color: white;
  transform-origin: center center;
  transition: transform 0.48s ease, opacity 0.48s ease;
}

.desktop-icon.zooming {
  transform: scale(4.2) translate(110px, 38px);
  opacity: 0.05;
}

.icon-art {
  width: 54px;
  height: 54px;
  border-radius: 12px;
  background:
    radial-gradient(circle at 35% 35%, #fff 0 14%, transparent 15%),
    linear-gradient(145deg, #ffd84f, #ff9d2f);
  box-shadow: 0 10px 18px rgba(0, 0, 0, 0.22);
}

.icon-label {
  text-align: center;
  font-size: 13px;
  line-height: 1.2;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
}

.login-window {
  position: relative;
  z-index: 2;
  width: min(100%, 430px);
  margin: 90px auto 0;
  border: 1px solid #0e2b63;
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 22px 60px rgba(0, 0, 0, 0.35);
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.98), rgba(189, 213, 246, 0.94));
}

.login-titlebar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 38px;
  padding: 8px 10px 8px 12px;
  background: linear-gradient(180deg, #4da3ff 0%, #1e66d0 45%, #0d3d9a 100%);
}

.login-title-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mini-icon {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background:
    radial-gradient(circle at 35% 35%, #fff 0 12%, transparent 13%),
    linear-gradient(145deg, #ffd84f, #ff9d2f);
}

.login-title-left strong {
  color: white;
  font-size: 13px;
}

.close-btn {
  width: 24px;
  height: 24px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 5px;
  background: linear-gradient(180deg, #ff8a7a, #d84937);
  color: white;
  font-size: 16px;
  line-height: 1;
}

.login-toolbar {
  display: flex;
  gap: 14px;
  padding: 6px 12px;
  background: linear-gradient(180deg, rgba(220, 236, 255, 0.96), rgba(190, 214, 247, 0.88));
  color: #133c89;
  font-size: 12px;
  border-bottom: 1px solid rgba(0, 34, 97, 0.18);
}

.login-body {
  padding: 22px 24px 24px;
}

.subtitle {
  margin: 0 0 16px;
  color: #1e478f;
  font-size: 14px;
  font-weight: 700;
}

input,
.generated-box {
  width: 100%;
  height: 50px;
  margin-top: 12px;
  padding: 0 16px;
  border: 1px solid #8aaee6;
  border-radius: 6px;
  background: white;
  color: #20498d;
  font-size: 16px;
  outline: none;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
}

input::placeholder {
  color: #7196db;
  font-style: italic;
  font-weight: 700;
}

.generated-box {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 14px;
}

.xp-btn {
  display: block;
  min-width: 182px;
  margin: 16px auto 0;
  padding: 10px 18px;
  border: 1px solid #2959b7;
  border-radius: 8px;
  background: linear-gradient(180deg, #f8fbff 0%, #cfe1fb 15%, #84b5ff 52%, #5f8fed 100%);
  color: #123f92;
  font-size: 16px;
  font-weight: 700;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.main-btn {
  margin-top: 18px;
}

.xp-btn:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.or-label {
  margin: 12px 0 -2px;
  text-align: center;
  color: #20498d;
  font-weight: 700;
}

.error {
  margin: 16px 0 0;
  text-align: center;
  color: #d64545;
  font-weight: 700;
}

.xp-pop-enter-active,
.xp-pop-leave-active {
  transition: opacity 0.24s ease, transform 0.24s ease;
}

.xp-pop-enter-from,
.xp-pop-leave-to {
  opacity: 0;
  transform: scale(0.94);
}

@media (max-width: 560px) {
  .desktop-page {
    padding: 12px;
  }

  .desktop-icon {
    left: 12px;
    top: 14px;
  }

  .login-window {
    margin-top: 76px;
  }

  .login-body {
    padding: 18px 14px 18px;
  }
}
</style>
