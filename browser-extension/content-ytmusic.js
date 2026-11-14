// Notch Bridge - YouTube Music Content Script
(() => {
  let lastState = {
    title: "",
    artist: "",
    isPlaying: false,
    duration: 0,
    position: 0
  };

  function parseTime(str) {
    if (!str) return 0;
    const parts = str.trim().split(":").map(Number);
    if (parts.length === 2) return parts[0] * 60 + parts[1];
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
    return 0;
  }

  function getMediaInfo() {
    const video = document.querySelector("video");
    const playerBar = document.querySelector("ytmusic-player-bar");
    if (!playerBar) return null;

    const titleEl = playerBar.querySelector(".title.ytmusic-player-bar");
    const bylineEl = playerBar.querySelector(".byline.ytmusic-player-bar");
    const imgEl = playerBar.querySelector("img.image.ytmusic-player-bar");
    const playPauseBtn = playerBar.querySelector("#play-pause-button");

    const title = titleEl ? titleEl.textContent.trim() : "";
    if (!title) return null;

    // Byline often has: "Artist • Album • 2024"
    let artist = "";
    let album = "";
    if (bylineEl) {
      const parts = bylineEl.textContent.split("•").map(s => s.trim());
      artist = parts[0] || "";
      if (parts.length > 1) album = parts[1];
    }

    const artUrl = imgEl ? imgEl.src : "";
    const isPlaying = playPauseBtn ? (playPauseBtn.getAttribute("aria-label")?.includes("Pause") || (!video?.paused && video?.currentTime > 0)) : false;

    let duration = video?.duration || 0;
    let position = video?.currentTime || 0;

    if (!duration || isNaN(duration)) {
      const timeInfo = playerBar.querySelector(".time-info.ytmusic-player-bar");
      if (timeInfo) {
        const [posStr, durStr] = timeInfo.textContent.split("/").map(s => s.trim());
        position = parseTime(posStr);
        duration = parseTime(durStr);
      }
    }

    return {
      type: "track_update",
      source: "YouTube Music",
      title: title,
      artist: artist,
      album: album,
      duration: duration || 0,
      position: position || 0,
      isPlaying: Boolean(isPlaying),
      artUrl: artUrl,
      trackId: window.location.href
    };
  }

  function checkAndUpdate() {
    const info = getMediaInfo();
    if (!info) return;

    const hasTrackChanged = info.title !== lastState.title || info.artist !== lastState.artist || Math.abs(info.duration - lastState.duration) > 2;
    const hasPlayStateChanged = info.isPlaying !== lastState.isPlaying;
    const hasPositionJumped = Math.abs(info.position - lastState.position) > 1.5;

    if (hasTrackChanged || hasPlayStateChanged || hasPositionJumped) {
      lastState = info;
      chrome.runtime.sendMessage(info).catch(() => {});
    } else {
      // Just send lightweight position update
      lastState.position = info.position;
      chrome.runtime.sendMessage({
        type: "position_update",
        position: info.position
      }).catch(() => {});
    }
  }

  // Poll state every 500ms
  setInterval(checkAndUpdate, 500);

  // Listen for media commands from desktop app
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || !msg.command) return;

    const playerBar = document.querySelector("ytmusic-player-bar");
    if (!playerBar) return;

    if (msg.command === "playpause") {
      const btn = playerBar.querySelector("#play-pause-button");
      btn?.click();
    } else if (msg.command === "next") {
      const btn = playerBar.querySelector(".next-button");
      btn?.click();
    } else if (msg.command === "previous") {
      const btn = playerBar.querySelector(".previous-button");
      btn?.click();
    }
  });

  console.log("[Notch Bridge] YouTube Music watcher active.");
})();
