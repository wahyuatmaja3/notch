import os
import json
from pathlib import Path

APPDATA_DIR = Path(os.environ.get("APPDATA", ".")) / "Notch"
SETTINGS_FILE = APPDATA_DIR / "settings.json"
CACHE_DIR = APPDATA_DIR / "cache"

DEFAULT_SETTINGS = {
    "theme": "Dark",
    "theme_style": "liquid_glass",        # "liquid_glass" or "obsidian"
    "layout_mode": "floating",            # "anchored" (top bezel flush) or "floating" (capsule)
    "floating_offset_y": 14,              # Distance from top edge in floating mode
    "opacity": 0.72,                      # Glass background opacity (0.3 - 0.95)
    "corner_radius": 24,
    "auto_accent": True,
    "custom_accent": "#1ED760",
    "active_module": "media",             # "media", "pomodoro", "tasks", "notifications", "hydration", "control_center"
    "enabled_modules": ["media", "pomodoro", "notifications", "tasks", "hydration", "control_center"],
    "split_pill_enabled": True,           # Show dual pill when 2 activities are active
    "privacy_indicators": True,           # Show mic/camera privacy dots
    
    # Media Player
    "show_album_art": True,
    "show_progress_bar": True,
    "show_lyrics": True,
    "show_controls": True,
    "collapsed_mode": "compact",          # "minimal", "compact", "lyrics"
    "collapsed_width": 320,
    "collapsed_height": 38,
    "expanded_width": 460,
    "expanded_height": 185,
    "auto_expand_on_new_song": True,
    "collapse_delay": 5.0,
    "lyrics_font_size": 13,
    "visible_lyric_lines": 3,
    "sync_offset_ms": 0,

    # Pomodoro Timer
    "pomodoro_focus_min": 25,
    "pomodoro_break_min": 5,
    "pomodoro_auto_switch": True,
    "pomodoro_sound_alert": True,

    # Hydration
    "hydration_target_l": 2.0,
    "hydration_interval_min": 45,

    # Notifications
    "auto_expand_notifications": True,
    "notification_alert_sec": 4.0,
    "notification_filter": ["whatsapp", "telegram", "discord", "spotify", "chrome", "firefox", "slack"],

    # General Placement
    "horizontal_alignment": "Center",
    "horizontal_offset": 0,
    "vertical_offset": 0,
    "start_with_windows": False,
    "acrylic_blur": False                  # Pure translucent composition is cleaner than legacy Vista DWM blur
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
