import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../pages/HomeView.vue";
import LobbyView from "../pages/LobbyView.vue";
import GameView from "../pages/GameView.vue";
import LeaderboardView from "../pages/LeaderboardView.vue";
import BlockchainView from "../pages/BlockchainView.vue";

const routes = [
  { path: "/", name: "home", component: HomeView },
  { path: "/lobby", name: "lobby", component: LobbyView },
  { path: "/game", name: "game", component: GameView },
  { path: "/leaderboard", name: "leaderboard", component: LeaderboardView },
  { path: "/blockchain", name: "blockchain", component: BlockchainView }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router;
