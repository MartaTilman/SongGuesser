import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";

async function bootstrap() {
  const app = createApp(App);

  app.use(createPinia());
  app.use(router);

  await router.isReady();
  app.mount("#app");
}

bootstrap();
