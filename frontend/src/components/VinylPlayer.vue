<template>
  <div class="player-card">
    <div class="vinyl-wrap">
      <div class="vinyl-stack">
        <div class="wmp-burst" aria-hidden="true">
          <span class="burst-core"></span>
          <span class="burst-ring"></span>
          <span class="burst-line line-one"></span>
          <span class="burst-line line-two"></span>
          <span class="burst-line line-three"></span>
        </div>

        <button
          v-if="playAudio"
          type="button"
          class="sound-toggle"
          :aria-label="isMuted ? 'Ukljuci zvuk' : 'Ugasi zvuk'"
          :title="isMuted ? 'Ukljuci zvuk' : 'Ugasi zvuk'"
          :class="{ muted: isMuted }"
          @click="toggleMute"
        >
          <span class="speaker-shape"></span>
          <span class="speaker-wave wave-one"></span>
          <span class="speaker-wave wave-two"></span>
        </button>

        <div class="vinyl" :class="{ spinning: isPlaying }">
          <div class="vinyl-inner"></div>
        </div>
      </div>
    </div>

    <p v-if="playAudio" class="status">
      {{ statusText }}
    </p>
    <p v-else class="status muted">
      Reprodukcija trenutno nije dostupna.
    </p>

    <button
      v-if="playAudio && showManualPlay"
      class="play-btn"
      type="button"
      @click="startPlayback"
    >
      Play
    </button>

    <div :id="playerElementId" class="youtube-player"></div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  youtubeId: {
    type: String,
    default: ""
  },
  startTime: {
    type: Number,
    default: 0
  },
  clipDuration: {
    type: Number,
    default: 0
  },
  clipStartedAt: {
    type: Number,
    default: 0
  },
  playAudio: {
    type: Boolean,
    default: false
  },
  countdownActive: {
    type: Boolean,
    default: false
  },
  initiallyMuted: {
    type: Boolean,
    default: false
  }
});

const player = ref(null);
const isPlaying = ref(false);
const isMuted = ref(props.initiallyMuted);
const autoStarted = ref(false);
const playerElementId = `youtube-player-${Math.random().toString(36).slice(2)}`;

let stopTimeout = null;
let autoStartInterval = null;

const effectiveStartSeconds = computed(() => {
  if (!props.clipStartedAt) {
    return props.startTime || 0;
  }

  const now = Date.now() / 1000;
  const elapsed = Math.max(0, now - props.clipStartedAt);
  return Math.floor((props.startTime || 0) + elapsed);
});

const showManualPlay = computed(() => {
  return !isPlaying.value && !props.countdownActive;
});

const statusText = computed(() => {
  if (props.countdownActive) {
    return "Priprema reprodukcije...";
  }

  if (isPlaying.value) {
    return isMuted.value ? "Pjesma svira bez zvuka" : "Pjesma svira";
  }

  return isMuted.value
    ? "Zvuk je ugasen. Ukljuci ga ikonom."
    : "Ako autoplay ne krene, klikni Play";
});

function clearStopTimeout() {
  if (stopTimeout) {
    clearTimeout(stopTimeout);
    stopTimeout = null;
  }
}

function clearAutoStartInterval() {
  if (autoStartInterval) {
    clearInterval(autoStartInterval);
    autoStartInterval = null;
  }
}

function syncMuteState() {
  if (!player.value) return;

  if (isMuted.value) {
    player.value.mute?.();
  } else {
    player.value.unMute?.();
    player.value.setVolume?.(100);
  }
}

function stopPlayback() {
  clearStopTimeout();

  if (player.value?.stopVideo) {
    player.value.stopVideo();
  }

  isPlaying.value = false;
}

function scheduleStop(durationMs) {
  clearStopTimeout();

  stopTimeout = setTimeout(() => {
    stopPlayback();
  }, durationMs);
}

function startPlayback() {
  if (!props.playAudio || !props.youtubeId || !player.value) {
    return;
  }

  const startedAt = props.clipStartedAt || Date.now() / 1000;
  const now = Date.now() / 1000;
  const elapsed = Math.max(0, now - startedAt);
  const remaining = Math.max(0, props.clipDuration - elapsed);

  if (remaining <= 0) {
    stopPlayback();
    return;
  }

  if (player.value.loadVideoById) {
    player.value.loadVideoById({
      videoId: props.youtubeId,
      startSeconds: effectiveStartSeconds.value
    });
  }

  setTimeout(() => {
    syncMuteState();

    if (player.value?.playVideo) {
      player.value.playVideo();
      isPlaying.value = true;
      autoStarted.value = true;
    }
  }, 250);

  scheduleStop(remaining * 1000);
}

function startAutoPlaybackWatcher() {
  clearAutoStartInterval();

  if (!props.playAudio || !props.youtubeId || !props.clipStartedAt) {
    return;
  }

  autoStartInterval = setInterval(() => {
    const now = Date.now() / 1000;

    if (!autoStarted.value && now >= props.clipStartedAt) {
      startPlayback();
      clearAutoStartInterval();
    }
  }, 150);
}

function toggleMute() {
  isMuted.value = !isMuted.value;
  syncMuteState();
}

function createPlayer() {
  if (!window.YT?.Player) return;

  player.value = new window.YT.Player(playerElementId, {
    height: "0",
    width: "0",
    videoId: props.youtubeId || "",
    playerVars: {
      autoplay: 0,
      controls: 0,
      disablekb: 1,
      fs: 0,
      modestbranding: 1,
      rel: 0
    },
    events: {
      onReady: () => {
        syncMuteState();
        startAutoPlaybackWatcher();
      },
      onStateChange: (event) => {
        if (!window.YT) return;

        if (event.data === window.YT.PlayerState.PLAYING) {
          isPlaying.value = true;
          syncMuteState();
        }

        if (
          event.data === window.YT.PlayerState.ENDED ||
          event.data === window.YT.PlayerState.PAUSED
        ) {
          isPlaying.value = false;
        }
      },
      onError: (event) => {
        console.error("YouTube player error:", event.data);
      }
    }
  });
}

function loadYouTubeApi() {
  if (window.YT?.Player) {
    createPlayer();
    return;
  }

  const existingScript = document.querySelector(
    'script[src="https://www.youtube.com/iframe_api"]'
  );

  if (!existingScript) {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
  }

  const previousReady = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = () => {
    if (typeof previousReady === "function") {
      previousReady();
    }
    createPlayer();
  };
}

watch(
  () => props.initiallyMuted,
  (value) => {
    isMuted.value = value;
    syncMuteState();
  }
);

watch(
  () => [props.youtubeId, props.startTime, props.clipDuration, props.clipStartedAt, props.playAudio],
  () => {
    autoStarted.value = false;
    isMuted.value = props.initiallyMuted;

    if (!player.value) return;

    syncMuteState();

    if (!props.playAudio) {
      stopPlayback();
      clearAutoStartInterval();
      return;
    }

    startAutoPlaybackWatcher();
  }
);

onMounted(() => {
  loadYouTubeApi();
});

onBeforeUnmount(() => {
  clearStopTimeout();
  clearAutoStartInterval();

  if (player.value?.destroy) {
    player.value.destroy();
  }

  player.value = null;
});
</script>

<style scoped>
.player-card {
  position: relative;
  text-align: center;
}

.vinyl-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 252px;
}

.vinyl-stack {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: min(100%, 430px);
  min-height: 252px;
  overflow: hidden;
  border: 1px solid rgba(251, 214, 230, 0.34);
  border-radius: 8px;
  background:
    radial-gradient(circle at 50% 52%, rgba(255, 255, 255, 0.18), transparent 20%),
    linear-gradient(180deg, rgba(48, 0, 18, 0.52), rgba(12, 0, 8, 0.34));
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.08),
    inset 0 0 34px rgba(255, 27, 89, 0.18),
    0 18px 34px rgba(0, 0, 0, 0.24);
}

.wmp-burst {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(circle at 50% 50%, #fff5f8 0 3%, #ffb8c8 4% 8%, rgba(203, 0, 45, 0.96) 9% 18%, transparent 19%),
    repeating-conic-gradient(from 18deg at 50% 50%, rgba(255, 255, 255, 0.92) 0deg 4deg, rgba(255, 72, 109, 0.72) 5deg 12deg, rgba(129, 0, 38, 0.95) 13deg 21deg),
    radial-gradient(circle at center, #faedf1 0 7%, #c90032 28%, #6e001e 66%, #16000a 100%);
  filter: saturate(1.18) contrast(1.08);
  animation: burstPulse 2.4s ease-in-out infinite alternate;
}

.wmp-burst::before,
.wmp-burst::after {
  content: "";
  position: absolute;
  inset: -18%;
  background:
    repeating-conic-gradient(from 0deg at 50% 50%, transparent 0deg 16deg, rgba(255, 255, 255, 0.32) 17deg 18deg, transparent 19deg 34deg);
  opacity: 0.8;
  mix-blend-mode: screen;
}

.wmp-burst::before {
  animation: burstSpin 8s linear infinite;
}

.wmp-burst::after {
  animation: burstSpin 12s linear infinite reverse;
  opacity: 0.46;
}

.burst-core,
.burst-ring,
.burst-line {
  position: absolute;
  left: 50%;
  top: 50%;
  pointer-events: none;
}

.burst-core {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: radial-gradient(circle, #ffffff 0 24%, #ff8ba8 25% 55%, rgba(163, 0, 43, 0) 70%);
  box-shadow:
    0 0 20px rgba(255, 255, 255, 0.95),
    0 0 56px rgba(255, 43, 95, 0.82);
  transform: translate(-50%, -50%);
  z-index: 1;
}

.burst-ring {
  width: 150px;
  height: 150px;
  border: 2px solid rgba(255, 255, 255, 0.72);
  border-radius: 48% 52% 46% 54%;
  transform: translate(-50%, -50%) rotate(-14deg);
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.72));
  z-index: 1;
}

.burst-line {
  width: 174px;
  height: 72px;
  border-top: 2px solid rgba(255, 255, 255, 0.78);
  border-radius: 50%;
  filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.8));
  z-index: 1;
}

.line-one {
  transform: translate(-50%, -50%) rotate(18deg);
}

.line-two {
  width: 128px;
  transform: translate(-50%, -50%) rotate(96deg);
}

.line-three {
  width: 208px;
  transform: translate(-50%, -50%) rotate(-34deg);
}

.sound-toggle {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 4;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 50%;
  background:
    radial-gradient(circle at 35% 25%, #ffffff 0 12%, #dcecff 34%, #5d9be8 100%);
  font-size: 0;
  line-height: 1;
  color: #134084;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 3px 10px rgba(0, 0, 0, 0.3);
}

.speaker-shape {
  position: absolute;
  left: 9px;
  top: 13px;
  width: 8px;
  height: 12px;
  background: #123e82;
  border-radius: 2px;
}

.speaker-shape::after {
  content: "";
  position: absolute;
  left: 6px;
  top: -3px;
  width: 0;
  height: 0;
  border-top: 9px solid transparent;
  border-bottom: 9px solid transparent;
  border-left: 11px solid #123e82;
}

.speaker-wave {
  position: absolute;
  top: 11px;
  border: 2px solid #123e82;
  border-left: 0;
  border-top-color: transparent;
  border-bottom-color: transparent;
  border-radius: 0 999px 999px 0;
}

.wave-one {
  left: 23px;
  width: 7px;
  height: 16px;
}

.wave-two {
  left: 27px;
  top: 8px;
  width: 10px;
  height: 22px;
}

.sound-toggle.muted .speaker-wave {
  display: none;
}

.sound-toggle.muted::after {
  content: "";
  position: absolute;
  left: 11px;
  top: 18px;
  width: 22px;
  height: 3px;
  border-radius: 999px;
  background: #bd1f35;
  transform: rotate(-38deg);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.35);
}

.vinyl {
  position: relative;
  z-index: 2;
  width: 196px;
  height: 196px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #e98e2b 0 12px, #0b1b2e 13px 18px, #e98e2b 19px 32px, #0c0f18 33px 100%),
    repeating-radial-gradient(circle at center, rgba(255, 255, 255, 0.05) 0 2px, rgba(0, 0, 0, 0.18) 3px 8px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow:
    0 18px 32px rgba(0, 0, 0, 0.42),
    0 0 0 8px rgba(8, 20, 44, 0.3),
    0 0 48px rgba(255, 255, 255, 0.2);
}

.vinyl.spinning {
  animation: spin 2s linear infinite;
}

.vinyl-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.status {
  min-height: 22px;
  margin: 18px 0 0;
  color: var(--xp-text-soft);
  font-size: 13px;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.status.muted {
  opacity: 0.85;
}

.play-btn {
  margin-top: 12px;
  padding: 12px 26px;
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 10px;
  background: linear-gradient(180deg, #4d99ff, #2f5fb9);
  color: white;
  font-size: 14px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.youtube-player {
  width: 0;
  height: 0;
  overflow: hidden;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@keyframes burstSpin {
  from {
    transform: rotate(0deg) scale(1);
  }

  to {
    transform: rotate(360deg) scale(1.08);
  }
}

@keyframes burstPulse {
  from {
    filter: saturate(1.08) contrast(1) brightness(0.94);
  }

  to {
    filter: saturate(1.28) contrast(1.12) brightness(1.1);
  }
}

@media (max-width: 720px) {
  .vinyl-stack {
    min-height: 236px;
  }

  .sound-toggle {
    right: 12px;
    bottom: 12px;
  }
}
</style>
