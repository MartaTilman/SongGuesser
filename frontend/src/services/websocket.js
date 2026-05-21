let socket = null;
let pendingMessages = [];

const WS_URL = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000";

export function connectWebSocket(
  lobbyId,
  playerName,
  onMessage,
  onOpen,
  onClose,
  avatar = "🎵"
) {
  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return socket;
  }

  const wsUrl = `${WS_URL}/ws/${encodeURIComponent(lobbyId)}/${encodeURIComponent(playerName)}?avatar=${encodeURIComponent(avatar)}`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    if (onOpen) onOpen();

    pendingMessages.forEach((payload) => {
      socket.send(JSON.stringify(payload));
    });
    pendingMessages = [];
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (onMessage) onMessage(data);
  };

  socket.onclose = () => {
    if (onClose) onClose();
    socket = null;
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
  };

  return socket;
}

export function sendWebSocketMessage(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
    return true;
  }

  if (socket && socket.readyState === WebSocket.CONNECTING) {
    pendingMessages.push(payload);
    return true;
  }

  return false;
}

export function closeWebSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }

  pendingMessages = [];
}
