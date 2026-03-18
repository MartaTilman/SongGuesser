<template>
  <div class="vinyl-wrap">
    <div class="notes">
      <span class="note">♪</span>
      <span class="note">♫</span>
      <span class="note">♪</span>
    </div>

    <div class="player">
      <div class="record" :class="{ spinning: isActuallyPlaying }">
        <div class="record-center"></div>
      </div>
      <div class="arm"></div>
    </div>

    <p class="status">
      {{ isActuallyPlaying ? "Pjesma svira..." : "Vrijeme za odgovore..." }}
    </p>

    <!-- skriveni YouTube player -->
    <div id="hidden-youtube-player" class="hidden-player"></div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, watch, ref } from "vue";

const props = defineProps({
  youtubeId: String,
  startTime: Number,
  clipDuration: Number,
  clipStartedAt: Number
});

const now = ref(Date.now() / 1000);
let timer = null;
let player = null;
let stopTimeout = null;

const isActuallyPlaying = computed(() => {
  const start = props.clipStartedAt || 0;
  const end = start + (props.clipDuration || 0);
  return now.value >= start && now.value <= end;
});

function loadYouTubeAPI() {
  return new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }

    if (document.getElementById("youtube-iframe-api")) {
      const oldReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (oldReady) oldReady();
        resolve();
      };
      return;
    }

    const tag = document.createElement("script");
    tag.id = "youtube-iframe-api";
    tag.src = "https://www.youtube.com/iframe_api";
    document.body.appendChild(tag);

    window.onYouTubeIframeAPIReady = () => resolve();
  });
}

function clearStopTimeout() {
  if (stopTimeout) {
    clearTimeout(stopTimeout);
    stopTimeout = null;
  }
}

function stopPlayback() {
  clearStopTimeout();

  try {
    if (player && typeof player.stopVideo === "function") {
      player.stopVideo();
    }
  } catch (e) {
    console.error("Stop playback error:", e);
  }
}

function scheduleStopFromNow(secondsLeft) {
  clearStopTimeout();

  if (secondsLeft <= 0) {
    stopPlayback();
    return;
  }

  stopTimeout = setTimeout(() => {
    stopPlayback();
  }, secondsLeft * 1000);
}

function startSyncedPlayback() {
  if (!player || !props.youtubeId) return;

  const clipStart = props.clipStartedAt || 0;
  const baseStartTime = props.startTime || 0;
  const clipDuration = props.clipDuration || 0;

  const currentTime = Date.now() / 1000;
  const elapsed = Math.max(0, currentTime - clipStart);

  if (elapsed >= clipDuration) {
    stopPlayback();
    return;
  }

  const seekTo = baseStartTime + elapsed;
  const secondsLeft = clipDuration - elapsed;

  try {
    player.loadVideoById({
      videoId: props.youtubeId,
      startSeconds: seekTo
    });

    setTimeout(() => {
      try {
        player.seekTo(seekTo, true);
        player.playVideo();
        scheduleStopFromNow(secondsLeft);
      } catch (e) {
        console.error("Playback sync error:", e);
      }
    }, 350);
  } catch (e) {
    console.error("Start synced playback error:", e);
  }
}

async function createPlayer() {
  await loadYouTubeAPI();

  if (player) {
    try {
      player.destroy();
    } catch (e) {
      console.error("Destroy player error:", e);
    }
    player = null;
  }

  player = new window.YT.Player("hidden-youtube-player", {
    height: "1",
    width: "1",
    videoId: props.youtubeId,
    playerVars: {
      autoplay: 1,
      controls: 0,
      disablekb: 1,
      fs: 0,
      modestbranding: 1,
      rel: 0,
      iv_load_policy: 3,
      start: props.startTime || 0
    },
    events: {
      onReady: () => {
        startSyncedPlayback();
      }
    }
  });
}

watch(
  () => [props.youtubeId, props.startTime, props.clipDuration, props.clipStartedAt],
  async ([youtubeId]) => {
    if (!youtubeId) return;
    await createPlayer();
  }
);

onMounted(async () => {
  timer = setInterval(() => {
    now.value = Date.now() / 1000;
  }, 250);

  if (props.youtubeId) {
    await createPlayer();
  }
});

onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  clearStopTimeout();

  if (player) {
    try {
      player.destroy();
    } catch (e) {
      console.error("Destroy on unmount error:", e);
    }
  }
});
</script>

<style scoped>
.vinyl-wrap {
  background: #1f2937;
  padding: 24px;
  border-radius: 18px;
  text-align: center;
}

.player {
  position: relative;
  width: 260px;
  height: 260px;
  margin: 20px auto;
}

.record {
  width: 220px;
  height: 220px;
  border-radius: 50%;
  margin: 0 auto;
  background:
    radial-gradient(circle at center, #222 0 20px, #b91c1c 20px 45px, #111 45px 100%);
  border: 8px solid #0f172a;
}

.record.spinning {
  animation: spin 2s linear infinite;
}

.record-center {
  width: 18px;
  height: 18px;
  background: #f3f4f6;
  border-radius: 50%;
  margin: 101px auto 0;
}

.arm {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 90px;
  height: 8px;
  background: #9ca3af;
  transform: rotate(35deg);
  transform-origin: right center;
  border-radius: 6px;
}

.notes {
  height: 28px;
  display: flex;
  justify-content: center;
  gap: 12px;
  font-size: 28px;
}

.note {
  animation: floatNote 1.8s ease-in-out infinite;
}

.note:nth-child(2) {
  animation-delay: 0.3s;
}

.note:nth-child(3) {
  animation-delay: 0.6s;
}

.status {
  margin-top: 10px;
  color: #d1d5db;
}

.hidden-player {
  width: 1px;
  height: 1px;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
  position: absolute;
  left: -9999px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes floatNote {
  0%, 100% { transform: translateY(0); opacity: 0.5; }
  50% { transform: translateY(-8px); opacity: 1; }
}
</style>