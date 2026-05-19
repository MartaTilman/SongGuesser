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

    <div class="xp-taskbar" aria-hidden="true">
      <div class="start-button"></div>
      <div class="taskbar-divider"></div>
      <div v-if="windowOpen" class="taskbar-item">
        <span class="taskbar-icon"></span>
        <span>Song Guesser</span>
      </div>
      <div class="taskbar-spacer"></div>
      <div class="taskbar-tray">
        <span class="tray-dot green"></span>
        <span class="tray-dot blue"></span>
        <span>{{ currentTime }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
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
const now = ref(new Date());

let clockInterval = null;

const currentTime = computed(() => {
  return now.value.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit"
  });
});

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
    if (
      err?.code === "ECONNABORTED" ||
      err?.message?.includes("timeout") ||
      err?.message === "Network Error"
    ) {
      error.value = "Ne mogu se spojiti na backend. Provjeri je li server pokrenut.";
    } else {
      error.value =
        err?.response?.data?.detail ||
        err?.message ||
        "Neuspjesno spajanje na lobby.";
    }
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

onMounted(() => {
  clockInterval = setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onBeforeUnmount(() => {
  if (clockInterval) {
    clearInterval(clockInterval);
    clockInterval = null;
  }
});
</script>

<style scoped>
.desktop-page {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  padding-bottom: 42px;
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
  border-radius: 50%;
  background: url("/logo-clean.png") center center / cover no-repeat;
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
  border-radius: 50%;
  background: url("/logo-clean.png") center center / cover no-repeat;
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

.xp-taskbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  height: 34px;
  padding: 0 8px 0 0;
  background:
    linear-gradient(180deg, #2a83f4 0%, #1b61d1 42%, #0f4cb5 100%);
  border-top: 1px solid rgba(171, 215, 255, 0.8);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.32),
    0 -2px 10px rgba(0, 25, 86, 0.22);
}

.start-button {
  width: 91px;
  height: 34px;
  flex: 0 0 91px;
  background: url("/Start_button_29.webp") left center / 91px 34px no-repeat;
  filter: drop-shadow(1px 0 1px rgba(0, 0, 0, 0.28));
}

.taskbar-divider {
  width: 1px;
  height: 24px;
  margin: 0 8px 0 6px;
  background: rgba(142, 190, 255, 0.58);
  box-shadow: 1px 0 0 rgba(0, 34, 115, 0.38);
}

.taskbar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 156px;
  max-width: 220px;
  height: 26px;
  padding: 0 12px 0 9px;
  border: 1px solid rgba(13, 56, 151, 0.7);
  border-radius: 3px;
  background: linear-gradient(180deg, #3d91ff 0%, #1d65d4 45%, #1552b9 100%);
  color: white;
  font-size: 12px;
  font-weight: 700;
  box-shadow:
    inset 1px 1px 0 rgba(255, 255, 255, 0.26),
    inset -1px -1px 0 rgba(0, 0, 0, 0.16);
}

.taskbar-icon {
  width: 17px;
  height: 17px;
  border-radius: 50%;
  background: url("/logo-clean.png") center center / cover no-repeat;
}

.taskbar-spacer {
  flex: 1;
}

.taskbar-tray {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 100%;
  min-width: 92px;
  padding: 0 10px;
  border-left: 1px solid rgba(164, 222, 255, 0.55);
  background: linear-gradient(180deg, #18a4ed 0%, #0d80d8 100%);
  color: white;
  font-size: 12px;
  font-weight: 700;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.35);
}

.tray-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.tray-dot.green {
  background: #78ff68;
}

.tray-dot.blue {
  background: #b4e8ff;
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
