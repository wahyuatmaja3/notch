import re
import sqlite3
import urllib.parse
import urllib.request
import json
from pathlib import Path
from config import CACHE_DIR

LRC_TIME_RE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
CLEAN_TITLE_RE = re.compile(r"\s*(\(|\[)(official|video|audio|lyrics|hd|4k|remastered|feat\.|ft\.).*?(\)|\])", re.IGNORECASE)

class LyricsEngine:
    def __init__(self):
        self.db_path = CACHE_DIR / "lyrics.db"
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS lyrics (
                        cache_key TEXT PRIMARY KEY,
                        title TEXT,
                        artist TEXT,
                        lrc_text TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
        except Exception as e:
            print(f"Failed to init SQLite lyrics db: {e}")

    def _cache_key(self, title: str, artist: str) -> str:
        return f"{artist.strip().lower()}___{title.strip().lower()}"

    def get_cached(self, title: str, artist: str):
        key = self._cache_key(title, artist)
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT lrc_text FROM lyrics WHERE cache_key = ? LIMIT 1", (key,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            print(f"Error reading cache: {e}")
        return None

    def save_cache(self, title: str, artist: str, lrc_text: str):
        key = self._cache_key(title, artist)
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO lyrics (cache_key, title, artist, lrc_text, created_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                    (key, title, artist, lrc_text)
                )
        except Exception as e:
            print(f"Error saving cache: {e}")

    def clean_title(self, title: str) -> str:
        if not title:
            return ""
        cleaned = CLEAN_TITLE_RE.sub("", title)
        return cleaned.strip(" -|~:")

    def fetch_lyrics(self, title: str, artist: str, duration_sec: int = 0):
        clean_t = self.clean_title(title)
        clean_a = artist.replace(" - Topic", "").strip()

        # Check cache
        cached = self.get_cached(clean_t, clean_a)
        if cached:
            return self.parse_lrc(cached)

        # Query LRCLIB API
        try:
            query = f"track_name={urllib.parse.quote(clean_t)}&artist_name={urllib.parse.quote(clean_a)}"
            if duration_sec > 0:
                query += f"&duration={int(duration_sec)}"
            url = f"https://lrclib.net/api/get?{query}"

            req = urllib.request.Request(url, headers={"User-Agent": "NotchDynamicIsland/1.0.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                synced = data.get("syncedLyrics")
                if synced:
                    self.save_cache(clean_t, clean_a, synced)
                    return self.parse_lrc(synced)
                plain = data.get("plainLyrics")
                if plain:
                    return self.parse_lrc(plain)
        except Exception:
            pass

        # Fallback search
        try:
            q = urllib.parse.quote(f"{clean_t} {clean_a}")
            search_url = f"https://lrclib.net/api/search?q={q}"
            req = urllib.request.Request(search_url, headers={"User-Agent": "NotchDynamicIsland/1.0.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                results = json.loads(resp.read().decode("utf-8"))
                if results and isinstance(results, list):
                    for item in results:
                        if item.get("syncedLyrics"):
                            s = item["syncedLyrics"]
                            self.save_cache(clean_t, clean_a, s)
                            return self.parse_lrc(s)
                    if results[0].get("plainLyrics"):
                        return self.parse_lrc(results[0]["plainLyrics"])
        except Exception:
            pass

        return []

    def parse_lrc(self, lrc_text: str):
        lines = []
        if not lrc_text:
            return lines

        has_timestamp = False
        for raw in lrc_text.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            m = LRC_TIME_RE.match(raw)
            if m:
                has_timestamp = True
                mins, secs, frac, text = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4).strip()
                millis = int(frac) * 10 if len(frac) == 2 else int(frac)
                total_ms = (mins * 60 + secs) * 1000 + millis
                lines.append({"ms": total_ms, "text": text})

        if not has_timestamp:
            for idx, raw in enumerate(lrc_text.splitlines()):
                t = raw.strip()
                if t:
                    lines.append({"ms": idx * 4000, "text": t})

        lines.sort(key=lambda x: x["ms"])
        return lines

    def get_active_index(self, lines, current_ms: int, offset_ms: int = 0):
        if not lines:
            return -1
        adjusted = current_ms + offset_ms
        active = -1
        for idx, line in enumerate(lines):
            if line["ms"] <= adjusted:
                active = idx
            else:
                break
        return active
