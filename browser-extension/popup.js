document.addEventListener("DOMContentLoaded", () => {
  const dot = document.getElementById("dot");
  const statusText = document.getElementById("status-text");
  const trackInfo = document.getElementById("track-info");

  chrome.runtime.sendMessage({ type: "get_status" }, (res) => {
    if (res && res.isConnected) {
      dot.classList.add("connected");
      statusText.textContent = "Connected to Notch";
      statusText.style.color = "#10B981";

      if (res.track && res.track.title) {
        trackInfo.textContent = `Now Playing: ${res.track.title} - ${res.track.artist}`;
      } else {
        trackInfo.textContent = "Ready. Waiting for playback.";
      }
    } else {
      dot.classList.remove("connected");
      statusText.textContent = "Not Connected";
      statusText.style.color = "#EF4444";
      trackInfo.textContent = "Make sure Notch desktop app is running.";
    }
  });
});
