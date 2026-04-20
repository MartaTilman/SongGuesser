<template>
  <div class="card player-card">
    <h3>Player</h3>

    <div class="vinyl-wrap">
      <div class="vinyl" :class="{ spinning: isPlaying }">
        <div class="vinyl-inner"></div>
      </div>
    </div>

    <p v-if="playAudio" class="status">
      {{ isPlaying ? "Reproducira se isječak..." : "Klikni Play za pokretanje zvuka" }}
    </p>
    <p v-else class="status muted">
      Samo host reproducira zvuk.
    </p>

    <button
      v-if="playAudio"
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
  }
});

const player = ref(null);
const isPlaying = ref(false);
const playerElementId = `youtube-player-${Math.random().toString(36).slice(2)}`;

let stopTimeout = null;

const effectiveStartSeconds = computed(() => {
  if (!props.clipStartedAt) {
    return props.startTime || 0;
  }

  const now = Date.now() / 1000;
  const elapsed = Math.max(0, now - props.clipStartedAt);
  return Math.floor((props.startTime || 0) + elapsed);
});

function clearStopTimeout() {
  if (stopTimeout) {
    clearTimeout(stopTimeout);
    stopTimeout = null;
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
    if (player.value?.playVideo) {
      player.value.playVideo();
      isPlaying.value = true;
    }
  }, 250);

  scheduleStop(remaining * 1000);
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
        console.log("YouTube player ready");
      },
      onStateChange: (event) => {
        if (!window.YT) return;

        if (event.data === window.YT.PlayerState.PLAYING) {
          isPlaying.value = true;
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
  () => [props.youtubeId, props.startTime, props.clipDuration, props.clipStartedAt, props.playAudio],
  () => {
    if (!player.value) return;

    if (!props.playAudio) {
      stopPlayback();
    }
  }
);

onMounted(() => {
  loadYouTubeApi();
});

onBeforeUnmount(() => {
  clearStopTimeout();

  if (player.value?.destroy) {
    player.value.destroy();
  }

  player.value = null;
});
</script>

<style scoped>
.card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}

.player-card {
  min-height: 320px;
}

.vinyl-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 24px 0;
}

.vinyl {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background:
    radial-gradient(circle at center, #111 0 18px, #d1d5db 19px 22px, #111 23px 100%),
    repeating-radial-gradient(circle at center, #111 0 6px, #1f2937 7px 10px);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
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
  text-align: center;
  color: #e5e7eb;
}

.status.muted {
  color: #9ca3af;
}

.play-btn {
  display: block;
  margin: 12px auto 0;
  padding: 10px 18px;
  border: none;
  border-radius: 10px;
  background: #16a34a;
  color: white;
  font-weight: 700;
  cursor: pointer;
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
</style>
