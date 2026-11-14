import os
import json
from pathlib import Path

APPDATA_DIR = Path(os.environ.get("APPDATA", ".")) / "Notch"
SETTINGS_FILE = APPDATA_DIR / "settings.json"
CACHE_DIR = APPDATA_DIR / "cache"

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "opacity": 0.68,
    "corner_radius": 22,
    "auto_accent": True,
    "custom_accent": "#1ED760",
    "show_album_art": True,
    "show_progress_bar": True,
    "show_lyrics": True,
    "show_controls": True,
    "horizontal_alignment": "Center",
    "horizontal_offset": 0,
    "vertical_offset": 0,
    "collapsed_mode": "compact",
    "collapsed_width": 320,
    "collapsed_height": 38,
    "expanded_width": 460,
    "expanded_height": 185,
    "auto_expand_on_new_song": True,
    "collapse_delay": 5.0,
    "start_with_windows": False,
    "lyrics_font_size": 13,
    "visible_lyric_lines": 3,
    "sync_offset_ms": 0,
    "acrylic_blur": True
}

class Config:
    def __init__(self):
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.data = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self.data.update(loaded)
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()
