<template>
  <div class="app-shell" :class="layoutMode">
    <div class="desktop-bg" aria-hidden="true">
      <video v-if="showVisualizerBg" class="desktop-video" autoplay muted loop playsinline>
        <source src="/lava-lamp.mp4" type="video/mp4" />
      </video>
      <div class="desktop-overlay" :class="{ soft: !showVisualizerBg }"></div>
    </div>

    <div v-if="layoutMode === 'desktop'" class="desktop-layer">
      <router-view />
    </div>

    <div v-else-if="layoutMode === 'xp'" class="xp-window">
      <header class="xp-titlebar">
        <div class="titlebar-left">
          <span class="xp-icon"></span>
          <strong>SongGuesser Lobby</strong>
        </div>

        <div class="titlebar-actions" aria-hidden="true">
          <span class="win-btn min"></span>
          <span class="win-btn max"></span>
          <span class="win-btn close"></span>
        </div>
      </header>

      <div class="xp-toolbar">
        <span>File</span>
        <span>Edit</span>
        <span>View</span>
        <span>Favorites</span>
        <span>Help</span>
      </div>

      <div class="xp-content">
        <router-view />
      </div>
    </div>

    <div v-else class="player-window">
      <header class="window-titlebar">
        <div class="titlebar-left">
          <span class="app-icon"></span>
          <div class="title-copy">
            <strong>SongGuesser Media Player</strong>
            <span>{{ currentTitle }}</span>
          </div>
        </div>

        <div class="titlebar-actions" aria-hidden="true">
          <span class="win-btn min"></span>
          <span class="win-btn max"></span>
          <span class="win-btn close"></span>
        </div>
      </header>

      <div class="window-toolbar">
        <span>File</span>
        <span>View</span>
        <span>Play</span>
        <span>Tools</span>
        <span>Help</span>
      </div>

      <div class="window-body">
        <aside class="window-sidebar">
          <div class="nav-group">
            <h3>Now Playing</h3>
            <button type="button">Song Guesser</button>
            <button type="button">Lobby Session</button>
            <button type="button">Top Hits</button>
          </div>

          <div class="nav-group">
            <h3>Media Library</h3>
            <button type="button">Recently Played</button>
            <button type="button">Rounds</button>
            <button type="button">Leaderboard</button>
          </div>
        </aside>

        <main class="window-content">
          <router-view />
        </main>
      </div>

      <footer class="window-status">
        <div class="status-left">
          <span class="status-led"></span>
          <span>Visualizations enabled</span>
        </div>
        <div class="status-right">
          <span>128 kbps</span>
          <span>stereo</span>
        </div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const layoutMode = computed(() => {
  if (route.name === "home") return "desktop";
  if (route.name === "lobby") return "xp";
  return "player";
});

const showVisualizerBg = computed(() => {
  return layoutMode.value === "player";
});

const currentTitle = computed(() => {
  const titleMap = {
    game: "Now playing",
    leaderboard: "Track results"
  };

  return titleMap[route.name] || "Now playing";
});
</script>

<style>
:root {
  --xp-blue-1: #1b4fb8;
  --xp-blue-2: #3c85ee;
  --xp-blue-3: #76b4ff;
  --xp-panel-dark: rgba(17, 33, 73, 0.88);
  --xp-panel-mid: rgba(28, 53, 107, 0.84);
  --xp-panel-soft: rgba(220, 235, 255, 0.88);
  --xp-line: rgba(166, 215, 255, 0.4);
  --xp-gold: #ffd261;
  --xp-text: #dbeeff;
  --xp-text-soft: #a9cbff;
  --xp-text-bright: #f4fbff;
  --xp-magenta: #d63aff;
  --xp-green: #7dff9b;
  --xp-red: #ff8b8b;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  min-height: 100%;
}

body {
  margin: 0;
  font-family: Tahoma, Verdana, Arial, sans-serif;
  color: var(--xp-text);
  background: linear-gradient(180deg, #204a87 0%, #3f7ed7 100%);
  overflow-x: hidden;
}

button,
input {
  font-family: inherit;
}

.app-shell {
  position: relative;
  min-height: 100vh;
}

.desktop-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(31, 81, 150, 0.2), rgba(11, 37, 84, 0.5)),
    linear-gradient(180deg, #315fa8 0%, #4d88dd 100%);
}

.desktop-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  opacity: 0.6;
  filter: saturate(1.15) brightness(0.52);
}

.desktop-overlay {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(92, 173, 255, 0.16), transparent 24%),
    radial-gradient(circle at 70% 70%, rgba(255, 66, 196, 0.12), transparent 20%),
    linear-gradient(180deg, rgba(6, 18, 50, 0.18), rgba(6, 18, 50, 0.35)),
    rgba(255, 255, 255, 0.08);
}

.desktop-overlay.soft {
  background:
    radial-gradient(circle at 18% 14%, rgba(255, 255, 255, 0.18), transparent 18%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(0, 28, 88, 0.14));
}

.desktop-layer {
  position: relative;
  z-index: 1;
  min-height: 100vh;
}

.xp-window,
.player-window {
  position: relative;
  z-index: 1;
  width: min(100%, 1180px);
  margin: 18px auto;
  border: 1px solid #0e2b63;
  border-radius: 10px;
  overflow: hidden;
  box-shadow:
    0 30px 90px rgba(0, 0, 0, 0.45),
    inset 0 0 0 1px rgba(255, 255, 255, 0.18);
}

.xp-window {
  min-height: calc(100vh - 36px);
  background: linear-gradient(180deg, rgba(232, 242, 255, 0.96), rgba(191, 215, 247, 0.92));
}

.player-window {
  min-height: 760px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, rgba(28, 59, 117, 0.95), rgba(12, 24, 53, 0.95));
}

.xp-titlebar,
.window-titlebar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 44px;
  padding: 8px 14px 8px 12px;
  background: linear-gradient(180deg, #4da3ff 0%, #1e66d0 45%, #0d3d9a 100%);
  border-bottom: 1px solid rgba(255, 255, 255, 0.22);
}

.window-titlebar {
  min-height: 58px;
  padding-left: 16px;
}

.titlebar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.xp-icon,
.app-icon {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  background:
    radial-gradient(circle at 35% 35%, #fff 0 12%, transparent 13%),
    linear-gradient(145deg, #ffd84f, #ff9d2f);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.app-icon {
  width: 28px;
  height: 28px;
  border-radius: 7px;
}

.xp-titlebar strong,
.title-copy strong {
  color: white;
  font-size: 14px;
  font-weight: 700;
}

.title-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.title-copy span {
  color: rgba(235, 246, 255, 0.85);
  font-size: 11px;
}

.titlebar-actions {
  display: flex;
  gap: 8px;
}

.win-btn {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.5), rgba(185, 219, 255, 0.18));
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

.win-btn.close {
  background: linear-gradient(180deg, #ff8a7a, #d84937);
}

.xp-toolbar,
.window-toolbar {
  display: flex;
  gap: 18px;
  padding: 8px 14px;
  background: linear-gradient(180deg, rgba(220, 236, 255, 0.96), rgba(190, 214, 247, 0.88));
  color: #133c89;
  font-size: 12px;
  border-bottom: 1px solid rgba(0, 34, 97, 0.18);
}

.xp-content {
  min-height: calc(100vh - 104px);
  padding: 18px;
}

.window-body {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
  background: linear-gradient(180deg, rgba(16, 34, 74, 0.88), rgba(8, 20, 44, 0.92));
}

.window-sidebar {
  padding: 16px 14px;
  background: linear-gradient(180deg, rgba(65, 110, 190, 0.5), rgba(12, 29, 66, 0.32));
  border-right: 1px solid rgba(162, 214, 255, 0.18);
}

.nav-group + .nav-group {
  margin-top: 18px;
}

.nav-group h3 {
  margin: 0 0 10px;
  color: #fff1b2;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.nav-group button {
  width: 100%;
  margin-bottom: 8px;
  padding: 10px 12px;
  text-align: left;
  border: 1px solid rgba(168, 215, 255, 0.2);
  border-radius: 8px;
  background: linear-gradient(180deg, rgba(88, 140, 226, 0.35), rgba(24, 52, 112, 0.24));
  color: var(--xp-text);
}

.window-content {
  min-width: 0;
  padding: 20px;
}

.window-status {
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 34px;
  padding: 6px 12px;
  background: linear-gradient(180deg, rgba(202, 223, 249, 0.95), rgba(156, 190, 236, 0.92));
  color: #163f8f;
  font-size: 11px;
  border-top: 1px solid rgba(255, 255, 255, 0.35);
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-led {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6bff82;
  box-shadow: 0 0 10px rgba(107, 255, 130, 0.8);
}

@media (max-width: 980px) {
  .window-body {
    grid-template-columns: 1fr;
  }

  .window-sidebar {
    display: none;
  }

  .player-window {
    min-height: auto;
  }
}

@media (max-width: 640px) {
  .xp-content,
  .window-content {
    padding: 10px;
  }

  .title-copy span {
    display: none;
  }

  .xp-toolbar,
  .window-toolbar {
    gap: 10px;
    font-size: 11px;
  }
}
</style>
