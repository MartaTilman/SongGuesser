import { defineStore } from "pinia";
import { connectWebSocket, sendWebSocketMessage, closeWebSocket } from "../services/websocket";
import api from "../services/api";

export const useGameStore = defineStore("game", {
  state: () => ({
    playerName: localStorage.getItem("playerName") || "",
    lobbyId: localStorage.getItem("lobbyId") || "",
    avatar: localStorage.getItem("avatar") || "🎵",

    connected: false,
    host: "",
    players: [],

    roundData: null,
    leaderboard: [],
    awardedPoints: [],
    finalLeaderboard: [],
    blockchain: [],
    blockchainValid: null,

    error: "",
    phase: "lobby" // lobby | round | leaderboard | finished
  }),

  getters: {
    isHost: (state) => state.playerName === state.host
  },

  actions: {
    setUserData({ playerName, lobbyId, avatar }) {
      this.playerName = playerName;
      this.lobbyId = lobbyId;
      this.avatar = avatar;

      localStorage.setItem("playerName", playerName);
      localStorage.setItem("lobbyId", lobbyId);
      localStorage.setItem("avatar", avatar);
    },

    connect() {
      if (!this.lobbyId || !this.playerName) return;

      connectWebSocket(
        this.lobbyId,
        this.playerName,
        this.handleMessage,
        () => {
          this.connected = true;
        },
        () => {
          this.connected = false;
        },
        this.avatar
      );
    },

    disconnect() {
      closeWebSocket();
      this.connected = false;
    },

    handleMessage(message) {
      if (message.type === "error") {
        this.error = message.message;
      }

      if (message.type === "lobby_update") {
        this.players = message.players || [];
        this.host = message.host || "";
        this.phase = "lobby";
      }

      if (message.type === "round_started") {
        this.roundData = message;
        this.phase = "round";
      }

      if (message.type === "leaderboard") {
        this.leaderboard = message.data || [];
        this.awardedPoints = message.awarded_points || [];
        this.roundData = {
          ...this.roundData,
          correct_title: message.correct_title,
          correct_artist: message.correct_artist
        };
        this.phase = "leaderboard";
      }

      if (message.type === "game_finished") {
        this.finalLeaderboard = message.leaderboard || [];
        this.phase = "finished";
      }
    },

    async fetchLobbyInfo() {
      const res = await api.get(`/lobby/${this.lobbyId}/info`);
      this.host = res.data.host;
      this.players = res.data.players || [];
    },

    async fetchBlockchain() {
      const res = await api.get(`/lobby/${this.lobbyId}/blockchain`);
      this.blockchain = res.data.chain || [];
      this.blockchainValid = res.data.valid;
    },

    startRound() {
      sendWebSocketMessage({ type: "start_round" });
    },

    submitAnswer(payload) {
  sendWebSocketMessage({
    type: "answer",
    title_answer: payload.title_answer,
    artist_answer: payload.artist_answer,
    year_answer: payload.year_answer
  });
},

    finishSong() {
      sendWebSocketMessage({ type: "finish_song" });
    },

    resetGame() {
      this.roundData = null;
      this.leaderboard = [];
      this.awardedPoints = [];
      this.finalLeaderboard = [];
      this.phase = "lobby";
    },

    clearAll() {
      this.disconnect();

      this.playerName = "";
      this.lobbyId = "";
      this.avatar = "🎵";
      this.host = "";
      this.players = [];
      this.roundData = null;
      this.leaderboard = [];
      this.awardedPoints = [];
      this.finalLeaderboard = [];
      this.blockchain = [];
      this.blockchainValid = null;
      this.error = "";
      this.phase = "lobby";

      localStorage.removeItem("playerName");
      localStorage.removeItem("lobbyId");
      localStorage.removeItem("avatar");
    }
  }
});