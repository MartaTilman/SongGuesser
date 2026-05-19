<template>
  <div class="player-card">
    <div class="vinyl-wrap">
      <div class="vinyl-stack">
        <div class="xp-visualizer" :class="{ active: isPlaying }" aria-hidden="true">
          <div class="viz-scope">
            <span class="scope-beam beam-one"></span>
            <span class="scope-beam beam-two"></span>
            <span class="scope-beam beam-three"></span>
            <span class="scope-beam beam-four"></span>
          </div>

          <div class="viz-bars">
            <span v-for="bar in 42" :key="bar" :style="{ '--bar': bar }"></span>
          </div>

          <div class="viz-ribbons">
            <span class="ribbon ribbon-one"></span>
            <span class="ribbon ribbon-two"></span>
            <span class="ribbon ribbon-three"></span>
          </div>
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
          <img
            class="sound-icon"
            :src="isMuted ? '/no_sound.png' : '/sound.png'"
            alt=""
            aria-hidden="true"
          />
        </button>

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
  border: 1px solid rgba(198, 230, 255, 0.44);
  border-radius: 8px;
  background:
    linear-gradient(180deg, rgba(4, 13, 33, 0.52), rgba(0, 0, 0, 0.2)),
    radial-gradient(circle at 50% 58%, rgba(20, 138, 255, 0.24), transparent 28%),
    linear-gradient(180deg, #02060e 0%, #07152f 50%, #010307 100%);
  box-shadow:
    inset 0 0 0 1px rgba(0, 0, 0, 0.78),
    inset 0 0 34px rgba(47, 139, 255, 0.22),
    0 18px 34px rgba(0, 0, 0, 0.24);
}

.xp-visualizer {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.xp-visualizer::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 4;
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.11), transparent 34%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.035) 0 1px, transparent 1px 4px);
  pointer-events: none;
}

.xp-visualizer::after {
  content: "";
  position: absolute;
  left: 18px;
  right: 18px;
  bottom: 16px;
  height: 34px;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, rgba(31, 201, 255, 0.34), transparent 70%);
  filter: blur(2px);
}

.viz-bars {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 32px;
  z-index: 2;
  height: 145px;
  display: grid;
  grid-template-columns: repeat(42, 1fr);
  gap: 3px;
  align-items: end;
}

.viz-bars span {
  min-height: 12px;
  border-radius: 3px 3px 0 0;
  background: linear-gradient(180deg, #fff56a 0%, #8dff6a 30%, #22d5ff 62%, #2f55ff 100%);
  box-shadow:
    0 0 8px rgba(56, 222, 255, 0.58),
    0 0 17px rgba(57, 93, 255, 0.32);
  animation: xpBar 0.72s ease-in-out infinite alternate;
  animation-delay: calc(var(--bar) * -0.045s);
}

.viz-bars span:nth-child(3n) {
  background: linear-gradient(180deg, #ff78d7 0%, #8dfbff 44%, #2b77ff 100%);
  animation-duration: 0.95s;
}

.viz-bars span:nth-child(5n) {
  background: linear-gradient(180deg, #fff59c 0%, #b6ff63 44%, #22a9ff 100%);
  animation-duration: 1.18s;
}

.viz-scope,
.viz-ribbons {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
}

.scope-beam,
.ribbon {
  position: absolute;
  left: -8%;
  right: -8%;
  border-radius: 50%;
  filter: drop-shadow(0 0 10px rgba(84, 220, 255, 0.75));
  opacity: 0.82;
}

.scope-beam {
  height: 86px;
  border-top: 2px solid rgba(118, 239, 255, 0.52);
}

.beam-one {
  bottom: 92px;
  transform: rotate(-4deg);
  animation: xpWave 3.5s ease-in-out infinite alternate;
}

.beam-two {
  bottom: 68px;
  border-color: rgba(255, 126, 214, 0.44);
  transform: rotate(5deg);
  animation: xpWave 3.1s ease-in-out infinite alternate-reverse;
}

.beam-three {
  bottom: 118px;
  border-color: rgba(255, 245, 110, 0.34);
  transform: rotate(2deg);
  animation: xpWave 4.4s ease-in-out infinite alternate;
}

.beam-four {
  bottom: 42px;
  border-color: rgba(111, 255, 155, 0.32);
  transform: rotate(-7deg);
  animation: xpWave 3.8s ease-in-out infinite alternate-reverse;
}

.ribbon {
  width: 150px;
  height: 150px;
  border: 2px solid rgba(139, 227, 255, 0.32);
  left: 50%;
  top: 46%;
  right: auto;
  transform: translate(-50%, -50%) rotate(-18deg);
}

.ribbon-one {
  animation: xpRibbon 8s linear infinite;
}

.ribbon-two {
  width: 230px;
  height: 82px;
  border-color: rgba(255, 116, 218, 0.28);
  animation: xpRibbon 10s linear infinite reverse;
}

.ribbon-three {
  width: 92px;
  height: 210px;
  border-color: rgba(255, 242, 110, 0.24);
  animation: xpRibbon 12s linear infinite;
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

.sound-icon {
  width: 23px;
  height: 23px;
  object-fit: contain;
  pointer-events: none;
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

@keyframes xpBar {
  from {
    height: 16px;
  }

  to {
    height: 142px;
  }
}

@keyframes xpWave {
  from {
    transform: translateX(-30px) rotate(-5deg) scaleY(0.78);
  }

  to {
    transform: translateX(30px) rotate(5deg) scaleY(1.08);
  }
}

@keyframes xpRibbon {
  from {
    transform: translate(-50%, -50%) rotate(0deg) scaleX(1);
  }

  to {
    transform: translate(-50%, -50%) rotate(360deg) scaleX(1.08);
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
