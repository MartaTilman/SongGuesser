let socket = null;
let pendingMessages = [];
let manualClose = false;

const WS_URL = import.meta.env.VITE_WS_URL || "ws://127.0.0.1:8000";

export function connectWebSocket(
  lobbyId,
  playerName,
  onMessage,
  onOpen,
  onClose,
  avatar = "🎵",
  wallet = {}
) {
  manualClose = false;

  if (
    socket &&
    (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)
  ) {
    return socket;
  }

  const params = new URLSearchParams({
    avatar
  });

  if (wallet.publicKey) {
    params.set("public_key", JSON.stringify(wallet.publicKey));
  }

  if (wallet.joinSignature) {
    params.set("join_signature", JSON.stringify(wallet.joinSignature));
  }

  const wsUrl = `${WS_URL}/ws/${encodeURIComponent(lobbyId)}/${encodeURIComponent(playerName)}?${params.toString()}`;

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
    manualClose = true;
    socket.close();
    socket = null;
  }

  pendingMessages = [];
}

export function wasManualClose() {
  return manualClose;
}
