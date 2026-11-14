// Notch Bridge - Background Service Worker

let socket = null;
let isConnected = false;
let currentTrack = null;
let reconnectTimer = null;

const WS_URL = "ws://127.0.0.1:7891";

function connectWebSocket() {
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  try {
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log("[Notch Bridge] Connected to Notch desktop app.");
      isConnected = true;
      if (currentTrack) {
        sendToApp(currentTrack);
      }
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("[Notch Bridge] Received command:", data);
        if (data.action) {
          forwardCommandToActiveTab(data.action);
        }
      } catch (e) {
        console.error("[Notch Bridge] Error handling message:", e);
      }
    };

    socket.onclose = () => {
      console.log("[Notch Bridge] Disconnected. Reconnecting in 3s...");
      isConnected = false;
      socket = null;
      scheduleReconnect();
    };

    socket.onerror = (err) => {
      console.warn("[Notch Bridge] WebSocket error (Notch app might not be running yet)");
      isConnected = false;
      socket = null;
      scheduleReconnect();
    };
  } catch (err) {
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connectWebSocket();
  }, 3000);
}

function sendToApp(payload) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(payload));
  }
}

function forwardCommandToActiveTab(command) {
  chrome.tabs.query({ url: ["https://music.youtube.com/*", "https://open.spotify.com/*"] }, (tabs) => {
    for (const tab of tabs) {
      chrome.tabs.sendMessage(tab.id, { command: command }).catch(() => {});
    }
  });
}

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "track_update" || msg.type === "position_update") {
    currentTrack = msg;
    sendToApp(msg);
  } else if (msg.type === "get_status") {
    sendResponse({ isConnected: isConnected, track: currentTrack });
  }
});

// Initial connection
connectWebSocket();
