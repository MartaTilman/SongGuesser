import { defineStore } from "pinia";
import {
  connectWebSocket,
  sendWebSocketMessage,
  closeWebSocket,
  wasManualClose
} from "../services/websocket";
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
    finalResultsReady: false,
    blockchain: [],
    blockchainValid: null,

    error: "",
    phase: "lobby",
    serverTimeOffset: 0,
    reconnectTimer: null
  }),

  getters: {
    isHost: (state) => state.playerName === state.host
  },

  actions: {
    setUserData({ playerName, lobbyId, avatar }) {
      this.playerName = playerName;
      this.lobbyId = String(lobbyId || "").trim().toUpperCase();
      this.avatar = avatar;

      localStorage.setItem("playerName", playerName);
      localStorage.setItem("lobbyId", this.lobbyId);
      localStorage.setItem("avatar", avatar);
    },

    async createLobby(playerName, avatar) {
      const res = await api.post("/lobbies");
      const generatedLobbyId = res.data?.lobby_id;

      if (!generatedLobbyId) {
        throw new Error("Generiranje lobby koda nije uspjelo.");
      }

      this.setUserData({
        playerName,
        lobbyId: generatedLobbyId,
        avatar
      });

      return generatedLobbyId;
    },

    async joinExistingLobby(playerName, lobbyId, avatar) {
      const normalizedLobbyId = String(lobbyId || "").trim().toUpperCase();

      if (!normalizedLobbyId) {
        throw new Error("Unesi lobby kod.");
      }

      const info = await api.get(`/lobby/${normalizedLobbyId}/info`);
      const normalizedPlayerName = String(playerName || "").trim().toLowerCase();
      const nameTaken = (info.data?.players || []).some((player) => {
        return (
          player.connected !== false &&
          String(player.name || "").trim().toLowerCase() === normalizedPlayerName
        );
      });

      if (nameTaken) {
        throw new Error("Ime je vec zauzeto u ovom lobbyju.");
      }

      this.setUserData({
        playerName,
        lobbyId: normalizedLobbyId,
        avatar
      });

      return normalizedLobbyId;
    },

    connect() {
      if (!this.lobbyId || !this.playerName) return;

      connectWebSocket(
        this.lobbyId,
        this.playerName,
        (message) => this.handleMessage(message),
        () => {
          this.connected = true;
          this.error = "";
          this.syncState();
          this.fetchLobbyState().catch(() => {});
        },
        () => {
          this.connected = false;

          if (wasManualClose() || !this.lobbyId || !this.playerName) {
            return;
          }

          if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
          }

          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
          }, 800);
        },
        this.avatar
      );
    },

    disconnect() {
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

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

        if (this.phase === "lobby" || message.game_number) {
          this.roundData = null;
          this.leaderboard = [];
          this.awardedPoints = [];
          this.finalLeaderboard = [];
          this.finalResultsReady = false;
          this.phase = "lobby";
        }
      }

      if (message.type === "round_started") {
        if (typeof message.server_time === "number") {
          this.serverTimeOffset = message.server_time - Date.now() / 1000;
        }

        this.roundData = message;
        this.leaderboard = [];
        this.awardedPoints = [];
        this.finalResultsReady = false;
        this.phase = "round";
      }

      if (message.type === "leaderboard") {
        this.leaderboard = message.data || [];
        this.awardedPoints = message.awarded_points || [];
        this.roundData = this.roundData
          ? {
              ...this.roundData,
              correct_title: message.correct_title,
              correct_artist: message.correct_artist,
              correct_year: message.correct_year,
              correct_decade: message.correct_decade
            }
          : null;
        this.phase = "leaderboard";
      }

      if (message.type === "game_finished") {
        this.finalLeaderboard = message.leaderboard || [];
        this.finalResultsReady = true;

        if (this.phase !== "leaderboard") {
          this.phase = "finished";
        }
      }
    },

    async fetchLobbyInfo() {
      const res = await api.get(`/lobby/${this.lobbyId}/info`);
      this.host = res.data.host || "";
      this.players = res.data.players || [];
    },

    async fetchLobbyState() {
      if (!this.lobbyId) return null;

      const res = await api.get(`/lobby/${this.lobbyId}/state`, {
        params: {
          player_name: this.playerName
        }
      });

      if (res.data?.message) {
        this.handleMessage(res.data.message);
      }

      return res.data;
    },

    async fetchBlockchain() {
      const res = await api.get(`/lobby/${this.lobbyId}/blockchain`);
      this.blockchain = res.data.chain || [];
      this.blockchainValid = res.data.valid;
    },

    startRound() {
      if (!this.connected) {
        this.connect();
      }

      const sent = sendWebSocketMessage({ type: "start_round" });

      if (!sent) {
        this.error = "Veza s lobbyjem nije aktivna. Pokusaj ponovno za trenutak.";
      }
    },

    requestGameReset() {
      if (!this.connected) {
        this.connect();
      }

      sendWebSocketMessage({ type: "reset_game" });
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

    showFinalResults() {
      if (this.finalResultsReady) {
        this.phase = "finished";
      }
    },

    syncState() {
      sendWebSocketMessage({ type: "sync_state" });
    },

    resetGame() {
      this.requestGameReset();
      this.roundData = null;
      this.leaderboard = [];
      this.awardedPoints = [];
      this.finalLeaderboard = [];
      this.finalResultsReady = false;
      this.phase = "lobby";
    },

    clearAll() {
      this.disconnect();

      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      this.playerName = "";
      this.lobbyId = "";
      this.avatar = "🎵";
      this.host = "";
      this.players = [];
      this.roundData = null;
      this.leaderboard = [];
      this.awardedPoints = [];
      this.finalLeaderboard = [];
      this.finalResultsReady = false;
      this.blockchain = [];
      this.blockchainValid = null;
      this.error = "";
      this.phase = "lobby";
      this.serverTimeOffset = 0;

      localStorage.removeItem("playerName");
      localStorage.removeItem("lobbyId");
      localStorage.removeItem("avatar");
    }
  }
});
