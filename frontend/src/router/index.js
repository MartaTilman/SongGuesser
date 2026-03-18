import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../pages/HomeView.vue";
import LobbyView from "../pages/LobbyView.vue";
import GameView from "../pages/GameView.vue";
import LeaderboardView from "../pages/LeaderboardView.vue";
import BlockchainView from "../pages/BlockchainView.vue";

const routes = [
  { path: "/", component: HomeView },
  { path: "/lobby", component: LobbyView },
  { path: "/game", component: GameView },
  { path: "/leaderboard", component: LeaderboardView },
  { path: "/blockchain", component: BlockchainView }
];

export default createRouter({
  history: createWebHistory(),
  routes
});