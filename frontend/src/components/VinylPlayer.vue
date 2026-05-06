<template>
  <div class="player-card">
    <div class="vinyl-wrap">
      <div class="vinyl-stack">
        <button
          v-if="playAudio"
          type="button"
          class="sound-toggle"
          :title="isMuted ? 'Ukljuci zvuk' : 'Ugasi zvuk'"
          @click="toggleMute"
        >
          {{ isMuted ? "🔇" : "🔊" }}
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
}

.vinyl-stack {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.sound-toggle {
  position: absolute;
  left: 18px;
  top: 118px;
  width: 42px;
  height: 42px;
  border: 1px solid rgba(176, 219, 255, 0.2);
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(66, 114, 201, 0.38), rgba(14, 36, 78, 0.48));
  font-size: 20px;
  line-height: 1;
  color: #9ddcff;
  box-shadow: 0 0 20px rgba(76, 175, 255, 0.16);
}

.vinyl {
  width: 196px;
  height: 196px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #e98e2b 0 12px, #0b1b2e 13px 18px, #e98e2b 19px 32px, #0c0f18 33px 100%),
    repeating-radial-gradient(circle at center, rgba(255, 255, 255, 0.05) 0 2px, rgba(0, 0, 0, 0.18) 3px 8px);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow:
    0 18px 32px rgba(0, 0, 0, 0.35),
    0 0 0 8px rgba(8, 20, 44, 0.3);
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

@media (max-width: 720px) {
  .sound-toggle {
    left: 6px;
    top: 128px;
  }
}
</style>
