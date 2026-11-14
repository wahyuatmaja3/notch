import asyncio
import io
import threading
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPixmap

try:
    import winsdk.windows.media.control as wmc
    import winsdk.windows.storage.streams as streams
    HAS_WINSDK = True
except ImportError:
    HAS_WINSDK = False


class MediaService(QObject):
    track_changed = pyqtSignal(dict)
    position_ticked = pyqtSignal(int)
    playback_state_changed = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.current_track = {
            "title": "No Track Playing",
            "artist": "Waiting for music...",
            "album": "",
            "duration_ms": 0,
            "position_ms": 0,
            "is_playing": False,
            "source": "Media",
            "pixmap": None
        }
        self._session_manager = None
        self._current_session = None
        self._loop = None
        self._thread = None

    def start(self):
        """Start dedicated background asyncio event loop for WinSDK SMTC."""
        if not HAS_WINSDK:
            print("[MediaService] WinSDK not available on this system.")
            return
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        asyncio.run_coroutine_threadsafe(self._async_init(), self._loop)

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    async def _async_init(self):
        try:
            self._session_manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
            if self._session_manager:
                self._update_session(self._session_manager.get_current_session())
                self._session_manager.add_current_session_changed(
                    lambda sender, args: self._loop.call_soon_threadsafe(self._on_session_changed_threadsafe)
                )
        except Exception as e:
            print(f"[MediaService] SMTC init error: {e}")

    def _on_session_changed_threadsafe(self):
        if self._session_manager:
            try:
                session = self._session_manager.get_current_session()
                self._update_session(session)
            except Exception as e:
                print(f"[MediaService] Session change error: {e}")

    def _update_session(self, session):
        self._current_session = session
        if session:
            try:
                session.add_media_properties_changed(
                    lambda s, a: asyncio.run_coroutine_threadsafe(self._refresh_properties(), self._loop)
                )
                session.add_timeline_properties_changed(lambda s, a: self._refresh_timeline())
                session.add_playback_info_changed(lambda s, a: self._refresh_playback())
            except Exception as e:
                print(f"[MediaService] Listener error: {e}")
            asyncio.run_coroutine_threadsafe(self._refresh_properties(), self._loop)
        else:
            self.current_track = {
                "title": "No Track Playing",
                "artist": "Waiting for music...",
                "album": "",
                "duration_ms": 0,
                "position_ms": 0,
                "is_playing": False,
                "source": "Media",
                "pixmap": None
            }
            self.track_changed.emit(self.current_track)

    async def _refresh_properties(self):
        if not self._current_session:
            return
        try:
            props = await self._current_session.try_get_media_properties_async()
            if not props:
                return

            timeline = self._current_session.get_timeline_properties()
            playback = self._current_session.get_playback_info()

            app_id = self._current_session.source_app_user_model_id or ""
            source = "Browser"
            lower_app = app_id.lower()
            if "chrome" in lower_app:
                source = "Chrome"
            elif "brave" in lower_app:
                source = "Brave"
            elif "firefox" in lower_app:
                source = "Firefox"
            elif "spotify" in lower_app:
                source = "Spotify"
            elif "edge" in lower_app:
                source = "Edge"

            thumb_bytes = None
            if props.thumbnail:
                try:
                    stream_ref = await props.thumbnail.open_read_async()
                    size = stream_ref.size
                    if size > 0:
                        reader = streams.DataReader(stream_ref)
                        await reader.load_async(size)
                        byte_array = bytearray(size)
                        reader.read_bytes(byte_array)
                        thumb_bytes = bytes(byte_array)
                except Exception as ex:
                    print(f"[MediaService] Error loading thumbnail: {ex}")

            is_playing = playback.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING if playback else False

            dur_ms = int(timeline.end_time.total_seconds() * 1000) if timeline and timeline.end_time else 0
            pos_ms = int(timeline.position.total_seconds() * 1000) if timeline and timeline.position else 0

            self.current_track = {
                "title": props.title or "Unknown Title",
                "artist": props.artist or "Unknown Artist",
                "album": props.album_title or "",
                "duration_ms": dur_ms,
                "position_ms": pos_ms,
                "is_playing": is_playing,
                "source": source,
                "thumb_bytes": thumb_bytes,
                "pixmap": None
            }

            self.track_changed.emit(self.current_track)
        except Exception as e:
            print(f"[MediaService] Error refreshing properties: {e}")

    def _refresh_timeline(self):
        session = self._current_session
        if not session:
            return
        try:
            timeline = session.get_timeline_properties()
            if timeline:
                pos_ms = int(timeline.position.total_seconds() * 1000)
                self.current_track["position_ms"] = pos_ms
                self.position_ticked.emit(pos_ms)
        except Exception:
            pass

    def _refresh_playback(self):
        session = self._current_session
        if not session:
            return
        try:
            playback = session.get_playback_info()
            if playback:
                is_playing = playback.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING
                self.current_track["is_playing"] = is_playing
                self.playback_state_changed.emit(is_playing)
        except Exception:
            pass

    def _get_active_session(self):
        if self._current_session:
            return self._current_session
        if self._session_manager:
            try:
                self._current_session = self._session_manager.get_current_session()
                return self._current_session
            except Exception:
                pass
        return None

    async def _async_play_pause(self):
        session = self._get_active_session()
        if session:
            try:
                await session.try_toggle_play_pause_async()
            except Exception as e:
                print(f"[MediaService] Play/pause error: {e}")

    async def _async_skip_next(self):
        session = self._get_active_session()
        if session:
            try:
                await session.try_skip_next_async()
            except Exception as e:
                print(f"[MediaService] Skip next error: {e}")

    async def _async_skip_previous(self):
        session = self._get_active_session()
        if session:
            try:
                await session.try_skip_previous_async()
            except Exception as e:
                print(f"[MediaService] Skip previous error: {e}")

    async def _async_seek(self, pos_ms: int):
        session = self._get_active_session()
        if session:
            try:
                import datetime
                pos_time = datetime.timedelta(milliseconds=pos_ms)
                await session.try_change_playback_position_async(pos_time)
            except Exception as e:
                print(f"[MediaService] Seek error: {e}")

    def play_pause(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_play_pause(), self._loop)

    def skip_next(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_skip_next(), self._loop)

    def skip_previous(self):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_skip_previous(), self._loop)

    def seek_to(self, pos_ms: int):
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_seek(pos_ms), self._loop)
