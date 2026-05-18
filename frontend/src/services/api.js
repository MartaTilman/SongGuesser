import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 4000
});

export async function waitForBackendReady(maxWaitMs = 30000) {
  const startedAt = Date.now();
  let lastError = null;

  while (Date.now() - startedAt < maxWaitMs) {
    try {
      await api.get("/");
      return true;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 800));
    }
  }

  throw lastError || new Error("Backend is not ready.");
}

export default api;
