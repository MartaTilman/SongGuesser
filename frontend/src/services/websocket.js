let socket = null;

export function connectWebSocket(lobbyId, playerName, onMessage, onOpen, onClose, avatar = "🎵") {
  if (socket && socket.readyState === WebSocket.OPEN) {
    return socket;
  }

  const wsUrl = `ws://127.0.0.1:8000/ws/${encodeURIComponent(lobbyId)}/${encodeURIComponent(playerName)}?avatar=${encodeURIComponent(avatar)}`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    if (onOpen) onOpen();
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
  }
}

export function closeWebSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }
}