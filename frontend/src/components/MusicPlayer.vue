<template>
  <div class="player-card">
    <h3>Trenutna pjesma</h3>
    <div id="yt-player"></div>
  </div>
</template>

<script setup>
import { onMounted, watch } from "vue";

const props = defineProps({
  youtubeId: String,
  startTime: Number,
  shouldPlay: Boolean
});

let player = null;

function loadYouTubeAPI() {
  return new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve();
      return;
    }

    const existing = document.getElementById("youtube-iframe-api");
    if (existing) {
      window.onYouTubeIframeAPIReady = resolve;
      return;
    }

    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    tag.id = "youtube-iframe-api";
    document.body.appendChild(tag);

    window.onYouTubeIframeAPIReady = resolve;
  });
}

function createPlayer() {
  if (!props.youtubeId) return;

  player = new window.YT.Player("yt-player", {
    height: "360",
    width: "100%",
    videoId: props.youtubeId,
    playerVars: {
      autoplay: props.shouldPlay ? 1 : 0,
      start: props.startTime || 0
    },
    events: {
      onReady: (event) => {
        if (props.shouldPlay) {
          event.target.seekTo(props.startTime || 0);
          event.target.playVideo();
        }
      }
    }
  });
}

onMounted(async () => {
  await loadYouTubeAPI();
  createPlayer();
});

watch(
  () => [props.youtubeId, props.startTime, props.shouldPlay],
  async () => {
    await loadYouTubeAPI();

    if (player && props.youtubeId) {
      player.loadVideoById({
        videoId: props.youtubeId,
        startSeconds: props.startTime || 0
      });

      if (!props.shouldPlay) {
        player.pauseVideo();
      }
    }
  }
);
</script>

<style scoped>
.player-card {
  background: #1f2937;
  padding: 20px;
  border-radius: 16px;
}
</style>