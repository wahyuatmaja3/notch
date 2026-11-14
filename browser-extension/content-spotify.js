// Notch Bridge - Spotify Web Content Script
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
    const titleEl = document.querySelector('[data-testid="context-item-info-title"]') || document.querySelector('[data-testid="now-playing-widget"] [dir="auto"]');
    const artistEl = document.querySelector('[data-testid="context-item-info-artist"]') || document.querySelector('[data-testid="context-item-info-subtitles"]');
    const imgEl = document.querySelector('[data-testid="cover-art-image"]');
    const playPauseBtn = document.querySelector('[data-testid="control-button-playpause"]');
    const posEl = document.querySelector('[data-testid="playback-position"]');
    const durEl = document.querySelector('[data-testid="playback-duration"]');

    const title = titleEl ? titleEl.textContent.trim() : "";
    if (!title) return null;

    const artist = artistEl ? artistEl.textContent.trim() : "";
    const artUrl = imgEl ? (imgEl.src || imgEl.srcset?.split(" ")[0] || "") : "";

    const isPlaying = playPauseBtn ? (playPauseBtn.getAttribute("aria-label")?.includes("Pause") || playPauseBtn.querySelector('path[d*="M2.7 1a.7"]')) : false;

    const position = posEl ? parseTime(posEl.textContent) : 0;
    const duration = durEl ? parseTime(durEl.textContent) : 0;

    return {
      type: "track_update",
      source: "Spotify",
      title: title,
      artist: artist,
      album: "",
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
      lastState.position = info.position;
      chrome.runtime.sendMessage({
        type: "position_update",
        position: info.position
      }).catch(() => {});
    }
  }

  setInterval(checkAndUpdate, 500);

  // Listen for media commands from desktop app
  chrome.runtime.onMessage.addListener((msg) => {
    if (!msg || !msg.command) return;

    if (msg.command === "playpause") {
      const btn = document.querySelector('[data-testid="control-button-playpause"]');
      btn?.click();
    } else if (msg.command === "next") {
      const btn = document.querySelector('[data-testid="control-button-skip-forward"]');
      btn?.click();
    } else if (msg.command === "previous") {
      const btn = document.querySelector('[data-testid="control-button-skip-back"]');
      btn?.click();
    }
  });

  console.log("[Notch Bridge] Spotify Web watcher active.");
})();
