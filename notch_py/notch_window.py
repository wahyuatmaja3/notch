"""
NotchWindow — Dynamic Island for Windows v2.0
Features:
- Pure Liquid Glass & Obsidian Themes (100% transparent corners, no black boxes)
- Anchored Mode (top bezel flush) & Floating Mode (capsule pill with customizable offset)
- Bottom Carousel Dots indicator & Swipe / Drag / Scroll gestures to switch modules
- 5 Integrated Modules: Media Player, Pomodoro Timer, Tasks & Reminders, Hydration, Control Center
- Live Synced 3-Line Lyrics, WinRT Notifications, SQLite Task Persistence
"""

import math
import time
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QPoint, QPointF, QSize
)
from PyQt6.QtWidgets import QWidget, QApplication, QInputDialog
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient,
    QPainterPath, QFont, QFontMetrics, QPixmap, QCursor
)
from qfluentwidgets import RoundMenu, Action

try:
    from color_thief import extract_accent_color
except ImportError:
    from notch_py.color_thief import extract_accent_color

try:
    from services import (
        PomodoroService, TaskService, HydrationService, SystemService, NotificationService
    )
except ImportError:
    from notch_py.services import (
        PomodoroService, TaskService, HydrationService, SystemService, NotificationService
    )


# ─────────────────────────────────────────────────────────────────────────────
# Layout Constants
# ─────────────────────────────────────────────────────────────────────────────
EXPANDED_W          = 460
EXPANDED_H          = 192
EXPANDED_R          = 26.0

COLLAPSED_MIN_W     = 200
COLLAPSED_COMPACT_W = 320
COLLAPSED_LYRIC_W   = 430
COLLAPSED_H         = 38

ANIM_MS = 280
MODULE_LIST = ["media", "pomodoro", "tasks", "hydration", "control_center"]


class NotchWindow(QWidget):
    open_settings_requested = pyqtSignal()

    def __init__(self, config, media_service, lyrics_engine,
                 pomodoro_service=None, task_service=None,
                 hydration_service=None, system_service=None,
                 notification_service=None):
        super().__init__()
        self.config        = config
        self.media_service = media_service
        self.lyrics_engine = lyrics_engine

        # Initialize or assign modular services
        self.pomodoro_service     = pomodoro_service or PomodoroService(config)
        self.task_service         = task_service or TaskService()
        self.hydration_service    = hydration_service or HydrationService(config)
        self.system_service       = system_service or SystemService()
        self.notification_service = notification_service or NotificationService(config)

        # Frameless, Always on Top, Tool window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)

        # Active state
        self._is_expanded       = False
        self._active_module     = self.config.get("active_module", "media")
        self._expanded_page     = "player"  # For media: "player" or "lyrics"
        self._layout_mode       = self.config.get("layout_mode", "floating")  # "anchored" or "floating"
        self._theme_style       = self.config.get("theme_style", "liquid_glass") # "liquid_glass" or "obsidian"
        self._collapsed_mode    = self.config.get("collapsed_mode", "compact")

        self._drag_pos          = QPoint()
        self._swipe_start_pos   = QPointF()
        self._swipe_triggered   = False
        self._accent            = QColor(config.get("custom_accent", "#1ED760"))
        self._wave_step         = 0.0

        # Media state
        self._title             = "Notch"
        self._artist            = "No track playing"
        self._is_playing        = False
        self._pos_ms            = 0
        self._dur_ms            = 0
        self._source            = "Spotify"
        self._pixmap            = None
        self._lyrics            = []
        self._lyric_idx         = -1
        self._lyric_text        = ""
        self._lyric_prev_text   = ""
        self._lyric_next_text   = ""
        self._lyric_opacity     = 1.0

        # Notification Banner state
        self._active_banner     = None
        self._banner_timeout    = 0.0

        # Hit testing & Hover tracking
        self._hover_target      = None
        self.setMouseTracking(True)

        # Window geometry tracking
        self._curr_w = self._get_collapsed_w()
        self._curr_h = COLLAPSED_H

        # Timers
        self.wave_timer = QTimer(self)
        self.wave_timer.setInterval(45)
        self.wave_timer.timeout.connect(self._on_wave)
        self.wave_timer.start()

        self.tick_timer = QTimer(self)
        self.tick_timer.setInterval(250)
        self.tick_timer.timeout.connect(self._on_tick)
        self.tick_timer.start()

        self.auto_collapse_timer = QTimer(self)
        self.auto_collapse_timer.setSingleShot(True)
        self.auto_collapse_timer.timeout.connect(self._auto_collapse)

        self.lyric_fade_timer = QTimer(self)
        self.lyric_fade_timer.setInterval(16)
        self.lyric_fade_timer.timeout.connect(self._on_lyric_fade)
        self._lyric_anim_step = 0

        self._connect_signals()
        self._position_to_screen()

    # ─────────────────── Module Navigation ───────────────────────────────────

    def next_module(self):
        try:
            idx = MODULE_LIST.index(self._active_module)
            new_idx = (idx + 1) % len(MODULE_LIST)
        except ValueError:
            new_idx = 0
        self.set_active_module(MODULE_LIST[new_idx])

    def prev_module(self):
        try:
            idx = MODULE_LIST.index(self._active_module)
            new_idx = (idx - 1) % len(MODULE_LIST)
        except ValueError:
            new_idx = 0
        self.set_active_module(MODULE_LIST[new_idx])

    def set_active_module(self, module_name: str):
        if module_name in MODULE_LIST:
            self._active_module = module_name
            self.config.set("active_module", module_name)
            if not self._is_expanded:
                self._position_to_screen()
            self.update()

    # ─────────────────── Geometry & Screen Positioning ───────────────────────

    def _get_collapsed_w(self) -> int:
        if self._active_banner:
            return 380
        if self._active_module == "pomodoro":
            return 220
        elif self._active_module == "tasks":
            return 240
        elif self._active_module == "hydration":
            return 220
        elif self._active_module == "control_center":
            return 240

        # Media module widths
        if self._collapsed_mode == "minimal":
            return COLLAPSED_MIN_W
        elif self._collapsed_mode == "lyrics":
            return COLLAPSED_LYRIC_W
        return COLLAPSED_COMPACT_W

    def _screen_center_x(self, w: int) -> int:
        try:
            screen = self.screen().geometry()
        except Exception:
            screen = QApplication.primaryScreen().geometry()
        align  = self.config.get("horizontal_alignment", "Center")
        offset = int(self.config.get("horizontal_offset", 0))
        if align == "Left":
            return 40 + offset
        elif align == "Right":
            return screen.width() - w - 40 + offset
        else:
            return (screen.width() - w) // 2 + offset

    def _screen_pos_y(self) -> int:
        if self._layout_mode == "anchored":
            return 0
        offset_y = int(self.config.get("floating_offset_y", 14))
        return max(0, offset_y)

    def _position_to_screen(self):
        w = EXPANDED_W if self._is_expanded else self._get_collapsed_w()
        h = EXPANDED_H if self._is_expanded else COLLAPSED_H
        self._curr_w = w
        self._curr_h = h
        x = self._screen_center_x(w)
        y = self._screen_pos_y()
        self.setGeometry(x, y, w, h)
        self.update()

    def apply_geometry_from_config(self):
        self._layout_mode    = self.config.get("layout_mode", "floating")
        self._theme_style    = self.config.get("theme_style", "liquid_glass")
        self._collapsed_mode = self.config.get("collapsed_mode", "compact")
        self._position_to_screen()

    # ─────────────────── Signals Connection ──────────────────────────────────

    def _connect_signals(self):
        # Media Service
        self.media_service.track_changed.connect(self._on_track_changed)
        self.media_service.position_ticked.connect(self._on_position_ticked)
        self.media_service.playback_state_changed.connect(self._on_playback_state_changed)
        self.lyrics_engine.lyrics_loaded.connect(self._on_lyrics_loaded)

        # Pomodoro Service
        self.pomodoro_service.tick.connect(self._on_pomo_tick)
        self.pomodoro_service.phase_completed.connect(self._on_pomo_phase_completed)

        # Task Service
        self.task_service.tasks_changed.connect(lambda _: self.update())

        # Hydration Service
        self.hydration_service.intake_updated.connect(lambda c, t: self.update())

        # Notification Service
        self.notification_service.notification_received.connect(self._on_notification_received)

    # ─────────────────── Callbacks ───────────────────────────────────────────

    def _on_notification_received(self, notif: dict):
        if self.config.get("auto_expand_notifications", True):
            self._active_banner = notif
            alert_sec = float(self.config.get("notification_alert_sec", 4.0))
            self._banner_timeout = time.time() + alert_sec
            if not self._is_expanded:
                self._position_to_screen()
            self.update()

    def _on_pomo_tick(self, left, total, phase):
        if self._active_module == "pomodoro":
            self.update()

    def _on_pomo_phase_completed(self, phase):
        self.notification_service.post_notification(
            "Pomodoro",
            f"{phase.capitalize()} Completed!",
            "Waktunya istirahat sejenak ☕" if phase == "focus" else "Kembali fokus kerja! 🎯"
        )

    def _on_lyrics_loaded(self, title: str, artist: str, lines: list):
        if title == self._title:
            self._lyrics = lines
            self._lyric_idx = -1
            self._update_lyric(self._pos_ms)
            self.update()

    def _on_track_changed(self, track: dict):
        self._title   = track.get("title", "No Track")
        self._artist  = track.get("artist", "")
        self._dur_ms  = track.get("duration_ms", 0)
        self._source  = track.get("source", "Spotify")

        thumb_bytes = track.get("thumb_bytes")
        if thumb_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(thumb_bytes)
            self._pixmap = pixmap if not pixmap.isNull() else None
        elif track.get("pixmap") and not track.get("pixmap").isNull():
            self._pixmap = track.get("pixmap")
        else:
            self._pixmap = None

        if self.config.get("auto_accent", True):
            self._accent = extract_accent_color(self._pixmap, self.config.get("custom_accent", "#1ED760"))
        else:
            self._accent = QColor(self.config.get("custom_accent", "#1ED760"))

        total_sec = self._dur_ms // 1000
        if self._title and self._title != "No Track Playing":
            self._lyric_idx       = -1
            self._lyric_text      = ""
            self._lyric_prev_text = ""
            self._lyric_next_text = ""
            self._lyrics = self.lyrics_engine.fetch_lyrics_async(self._title, self._artist, total_sec)
        else:
            self._lyrics = []

        if self.config.get("auto_expand_on_new_song", True) and self._title != "No Track Playing":
            if self._active_module == "media":
                self.expand()
                delay = float(self.config.get("collapse_delay", 5.0))
                self.auto_collapse_timer.start(int(delay * 1000))

        self.update()

    def _on_position_ticked(self, pos_ms: int):
        self._pos_ms = pos_ms
        self._update_lyric(pos_ms)
        if self._active_module == "media":
            self.update()

    def _on_playback_state_changed(self, is_playing: bool):
        self._is_playing = is_playing
        self.update()

    def _on_tick(self):
        # Auto-dismiss notification banner
        if self._active_banner and time.time() > self._banner_timeout:
            self._active_banner = None
            if not self._is_expanded:
                self._position_to_screen()
            self.update()

        track = self.media_service.current_track
        if track.get("is_playing", False) and self._dur_ms > 0:
            track["position_ms"] = track.get("position_ms", 0) + 250
            self._on_position_ticked(track["position_ms"])

    def _on_wave(self):
        if self._is_playing:
            self._wave_step += 0.28
            self.update()

    def _update_lyric(self, pos_ms: int):
        if not self._lyrics:
            return
        idx = self.lyrics_engine.get_active_index(
            self._lyrics, pos_ms, self.config.get("sync_offset_ms", 0)
        )
        if idx != self._lyric_idx and 0 <= idx < len(self._lyrics):
            self._lyric_idx       = idx
            self._lyric_text      = self._lyrics[idx]["text"]
            self._lyric_prev_text = self._lyrics[idx - 1]["text"] if idx > 0 else ""
            self._lyric_next_text = self._lyrics[idx + 1]["text"] if idx + 1 < len(self._lyrics) else ""
            self._lyric_opacity   = 0.0
            self._lyric_anim_step = 0
            self.lyric_fade_timer.start()

    def _on_lyric_fade(self):
        self._lyric_anim_step += 1
        t = min(self._lyric_anim_step / 14.0, 1.0)
        self._lyric_opacity = t * t * (3 - 2 * t)
        if self._lyric_anim_step >= 14:
            self._lyric_opacity = 1.0
            self.lyric_fade_timer.stop()
        self.update()

    # ─────────────────── Expand / Collapse ───────────────────────────────────

    def expand(self):
        if self._is_expanded:
            return
        self._is_expanded = True
        self._animate_to(EXPANDED_W, EXPANDED_H)

    def collapse(self):
        if not self._is_expanded:
            return
        self._is_expanded = False
        self._animate_to(self._get_collapsed_w(), COLLAPSED_H)

    def toggle_expand(self):
        self.collapse() if self._is_expanded else self.expand()

    def _animate_to(self, target_w: int, target_h: int):
        x = self._screen_center_x(target_w)
        y = self._screen_pos_y()
        end_rect = QRect(x, y, target_w, target_h)
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(ANIM_MS)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(end_rect)
        self.anim.valueChanged.connect(self._on_anim_step)
        self.anim.finished.connect(self._on_anim_done)
        self.anim.start()

    def _on_anim_step(self, val):
        self._curr_w = val.width()
        self._curr_h = val.height()
        self.update()

    def _on_anim_done(self):
        self._curr_w = self.width()
        self._curr_h = self.height()

    def _auto_collapse(self):
        if not self._is_expanded:
            return
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        self.collapse()

    # ─────────────────── Painting: Base Window Geometry ──────────────────────

    def _create_collapsed_path(self, w: float, h: float) -> QPainterPath:
        path = QPainterPath()
        if self._layout_mode == "anchored":
            flare_w = 26.0
            flare_h = 16.0
            r = 16.0
            path.moveTo(0, 0)
            path.cubicTo(flare_w * 0.45, 0, flare_w, flare_h * 0.45, flare_w, flare_h)
            path.lineTo(flare_w, h - r)
            path.quadTo(flare_w, h, flare_w + r, h)
            path.lineTo(w - flare_w - r, h)
            path.quadTo(w - flare_w, h, w - flare_w, h - r)
            path.lineTo(w - flare_w, flare_h)
            path.cubicTo(w - flare_w, flare_h * 0.45, w - flare_w * 0.45, 0, w, 0)
            path.lineTo(0, 0)
            path.closeSubpath()
        else:
            path.addRoundedRect(0, 0, w, h, h / 2.0, h / 2.0)
        return path

    def _create_expanded_path(self, w: float, h: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, EXPANDED_R, EXPANDED_R)
        return path

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        bw = float(self.width())
        bh = float(self.height())

        # 1. Background Fill (Liquid Glass vs Obsidian)
        shape_path = self._create_expanded_path(bw, bh) if self._is_expanded else self._create_collapsed_path(bw, bh)
        self._paint_background_glass(p, shape_path, bw, bh)

        # 2. Content Rendering
        if self._is_expanded:
            self._paint_expanded_view(p, bw, bh)
        else:
            self._paint_collapsed_view(p, bw, bh)

        p.end()

    def _paint_background_glass(self, p: QPainter, path: QPainterPath, bw: float, bh: float):
        if self._theme_style == "obsidian":
            p.fillPath(path, QColor(8, 9, 12, 248))
            p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
            p.drawPath(path)
            return

        # Liquid Glass Mode
        op = float(self.config.get("opacity", 0.72))
        alpha = int(max(0.3, min(0.95, op)) * 255)
        base_color = QColor(14, 17, 24, alpha)
        p.fillPath(path, base_color)

        # Specular Curved Glare at top edge
        glare = QLinearGradient(0, 0, 0, min(36.0, bh))
        glare.setColorAt(0.0, QColor(255, 255, 255, 45))
        glare.setColorAt(0.2, QColor(255, 255, 255, 18))
        glare.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillPath(path, QBrush(glare))

        # Dynamic Ambient Tint from active module / album accent
        ac = self._get_module_accent()
        glow = QRadialGradient(bw * 0.5, bh * 0.88, bw * 0.6)
        glow.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 115))
        glow.setColorAt(0.6, QColor(ac.red(), ac.green(), ac.blue(), 25))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillPath(path, QBrush(glow))

        # Glass Rim Border (1.2px)
        p.setPen(QPen(QColor(255, 255, 255, 38), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def _get_module_accent(self) -> QColor:
        if self._active_banner:
            return QColor("#25D366")  # WhatsApp neon green
        if self._active_module == "pomodoro":
            return QColor("#FF5722")  # Focus orange/coral
        elif self._active_module == "tasks":
            return QColor("#3F51B5")  # Indigo
        elif self._active_module == "hydration":
            return QColor("#00BCD4")  # Cyan water
        elif self._active_module == "control_center":
            return QColor("#9C27B0")  # Purple
        return self._accent           # Music dynamic accent

    # ─────────────────── Paint: Collapsed View ───────────────────────────────

    def _paint_collapsed_view(self, p: QPainter, bw: float, bh: float):
        flare_w = 26.0 if self._layout_mode == "anchored" else 0.0

        if self._active_banner:
            self._paint_collapsed_notification_banner(p, bw, bh, flare_w)
            return

        if self._active_module == "pomodoro":
            self._paint_collapsed_pomodoro(p, bw, bh, flare_w)
        elif self._active_module == "tasks":
            self._paint_collapsed_tasks(p, bw, bh, flare_w)
        elif self._active_module == "hydration":
            self._paint_collapsed_hydration(p, bw, bh, flare_w)
        elif self._active_module == "control_center":
            self._paint_collapsed_control_center(p, bw, bh, flare_w)
        else:
            self._paint_collapsed_media(p, bw, bh, flare_w)

    def _paint_collapsed_notification_banner(self, p: QPainter, bw: float, bh: float, flare_w: float):
        notif = self._active_banner
        art_x = flare_w + 12.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#25D366"))
        p.drawEllipse(QPointF(art_x + 8, bh / 2), 6, 6)

        p.setPen(QColor(255, 255, 255, 245))
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        p.setFont(font)
        text = f"{notif.get('app_name')}: {notif.get('title')} — {notif.get('message')}"
        fm = QFontMetrics(font)
        elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(bw - art_x - 36))
        p.drawText(QRectF(art_x + 22, 0, bw - art_x - 36, bh), Qt.AlignmentFlag.AlignVCenter, elided)

    def _paint_collapsed_pomodoro(self, p: QPainter, bw: float, bh: float, flare_w: float):
        left_x = flare_w + 14.0
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x, 0, 20, bh), Qt.AlignmentFlag.AlignVCenter, "🍅")

        mins = self.pomodoro_service.seconds_left // 60
        secs = self.pomodoro_service.seconds_left % 60
        time_str = f"{mins:02d}:{secs:02d}"
        phase_lbl = "Focus" if self.pomodoro_service.phase == "focus" else "Break"
        
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x + 24, 0, 110, bh), Qt.AlignmentFlag.AlignVCenter, f"{phase_lbl} {time_str}")

        pct = 1.0 - (self.pomodoro_service.seconds_left / max(1, self.pomodoro_service.total_seconds))
        ring_x = bw - flare_w - 24
        p.setPen(QPen(QColor(255, 255, 255, 40), 2.5))
        p.drawEllipse(QPointF(ring_x, bh / 2), 6.5, 6.5)
        p.setPen(QPen(QColor("#FF5722"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(ring_x - 6.5, bh / 2 - 6.5, 13, 13), 90 * 16, int(-pct * 360 * 16))

    def _paint_collapsed_tasks(self, p: QPainter, bw: float, bh: float, flare_w: float):
        left_x = flare_w + 14.0
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x, 0, 20, bh), Qt.AlignmentFlag.AlignVCenter, "📋")

        tasks = self.task_service.get_tasks()
        remaining = sum(1 for t in tasks if not t.get("completed"))
        msg = f"{remaining} tasks pending" if remaining > 0 else "All tasks done! ✓"
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x + 24, 0, bw - left_x - 30, bh), Qt.AlignmentFlag.AlignVCenter, msg)

    def _paint_collapsed_hydration(self, p: QPainter, bw: float, bh: float, flare_w: float):
        left_x = flare_w + 14.0
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x, 0, 20, bh), Qt.AlignmentFlag.AlignVCenter, "💧")

        cur = self.hydration_service.current_l
        tgt = self.hydration_service.target_l
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 240))
        p.drawText(QRectF(left_x + 24, 0, bw - left_x - 30, bh), Qt.AlignmentFlag.AlignVCenter, f"{cur:.2f} / {tgt:.1f} L")

    def _paint_collapsed_control_center(self, p: QPainter, bw: float, bh: float, flare_w: float):
        left_x = flare_w + 14.0
        vol = self.system_service.get_volume()
        bat = self.system_service.get_battery_info()
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 240))
        bat_str = f" • 🔋 {bat['percent']}%" if bat.get("has_battery") else ""
        p.drawText(QRectF(left_x, 0, bw - left_x - 14, bh), Qt.AlignmentFlag.AlignVCenter, f"🔊 {vol}%{bat_str}")

    def _paint_collapsed_media(self, p: QPainter, bw: float, bh: float, flare_w: float):
        art_sz = 24.0
        art_x = flare_w + 8.0
        art_y = (bh - art_sz) / 2
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 6, 6)

        if self._pixmap:
            p.save()
            p.setClipPath(art_path)
            scaled = self._pixmap.scaled(
                int(art_sz), int(art_sz),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            p.drawPixmap(int(art_x), int(art_y), scaled)
            p.restore()
        else:
            ac = self._accent
            art_grad = QLinearGradient(art_x, art_y, art_x + art_sz, art_y + art_sz)
            art_grad.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 230))
            art_grad.setColorAt(1.0, QColor(max(0, ac.red() - 40), max(0, ac.green() - 40), max(0, ac.blue() - 40), 230))
            p.fillPath(art_path, QBrush(art_grad))
            p.setPen(QColor(255, 255, 255, 220))
            p.setFont(QFont("Segoe UI Emoji", 10))
            p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "♫")

        p.setPen(QPen(QColor(255, 255, 255, 35), 0.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(art_path)

        wave_w = 26.0
        wave_right = bw - flare_w - 8.0
        wave_x = wave_right - wave_w
        self._draw_equalizer_bars(p, wave_x, bh / 2, wave_w, 16.0)

        content_left = art_x + art_sz + 8.0
        content_w = wave_x - content_left - 8.0

        if self._collapsed_mode == "compact" and content_w > 20:
            p.setPen(QColor(255, 255, 255, 240))
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            p.setFont(font)
            fm = QFontMetrics(font)
            text = f"{self._title} • {self._artist}" if self._artist else self._title
            elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(content_w))
            p.drawText(QRectF(content_left, 0, content_w, bh), Qt.AlignmentFlag.AlignVCenter, elided)
        elif self._collapsed_mode == "lyrics" and content_w > 20:
            lyric = self._lyric_text if self._lyric_text else (f"{self._title} • {self._artist}" if self._artist else self._title)
            p.save()
            p.setOpacity(self._lyric_opacity)
            p.setPen(QColor(255, 255, 255, 245))
            font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
            p.setFont(font)
            fm = QFontMetrics(font)
            elided = fm.elidedText(lyric, Qt.TextElideMode.ElideRight, int(content_w))
            p.drawText(QRectF(content_left, 0, content_w, bh), Qt.AlignmentFlag.AlignVCenter, elided)
            p.restore()

    def _draw_equalizer_bars(self, p: QPainter, x: float, y_center: float, total_w: float, max_h: float):
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._accent)
        bar_w = 3.2
        spacing = (total_w - (bar_w * 4)) / 3.0
        h_factors = [0.45, 0.90, 0.65, 0.80] if self._is_playing else [0.25, 0.25, 0.25, 0.25]
        for i in range(4):
            factor = h_factors[i]
            if self._is_playing:
                wave_mod = math.sin(self._wave_step + (i * 0.9)) * 0.35
                factor = max(0.18, min(1.0, factor + wave_mod))
            bar_h = max_h * factor
            bx = x + i * (bar_w + spacing)
            by = y_center - (bar_h / 2.0)
            p.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)
        p.restore()

    # ─────────────────── Paint: Expanded View ────────────────────────────────

    def _paint_expanded_view(self, p: QPainter, bw: float, bh: float):
        # 1. Close button '✕' at top right
        close_x = bw - 20
        p.setPen(QPen(QColor(255, 255, 255, 180), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(close_x - 10, 18), QPointF(close_x - 2, 26))
        p.drawLine(QPointF(close_x - 2, 18), QPointF(close_x - 10, 26))

        # 2. Render active module content
        if self._active_module == "pomodoro":
            self._paint_expanded_pomodoro(p, bw, bh)
        elif self._active_module == "tasks":
            self._paint_expanded_tasks(p, bw, bh)
        elif self._active_module == "hydration":
            self._paint_expanded_hydration(p, bw, bh)
        elif self._active_module == "control_center":
            self._paint_expanded_control_center(p, bw, bh)
        else:
            self._paint_expanded_media(p, bw, bh)

        # 3. Bottom Carousel Dots
        self._draw_carousel_dots(p, bw, bh - 13.0)

    def _draw_carousel_dots(self, p: QPainter, bw: float, dot_y: float):
        """Draws carousel indicator dots for module paging matching user design."""
        n = len(MODULE_LIST)
        spacing = 15.0
        start_x = (bw - ((n - 1) * spacing)) / 2.0
        curr_idx = MODULE_LIST.index(self._active_module) if self._active_module in MODULE_LIST else 0

        for i in range(n):
            dx = start_x + (i * spacing)
            p.setPen(Qt.PenStyle.NoPen)
            if i == curr_idx:
                p.setBrush(QColor(255, 255, 255, 240))
                p.drawRoundedRect(QRectF(dx - 5.0, dot_y - 2.0, 10.0, 4.0), 2.0, 2.0)
            else:
                p.setBrush(QColor(255, 255, 255, 75))
                p.drawEllipse(QPointF(dx, dot_y), 2.2, 2.2)

    # ─────────────────── Paint: Expanded Media (Image 1 Replica) ─────────────

    def _paint_expanded_media(self, p: QPainter, bw: float, bh: float):
        # 1. Album Art Squircle (52x52, r=12)
        art_sz = 52.0
        art_x = 22.0
        art_y = 16.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 12, 12)

        if self._pixmap:
            p.save()
            p.setClipPath(art_path)
            scaled = self._pixmap.scaled(
                int(art_sz), int(art_sz),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            p.drawPixmap(int(art_x), int(art_y), scaled)
            p.restore()
        else:
            ac = self._accent
            art_grad = QLinearGradient(art_x, art_y, art_x + art_sz, art_y + art_sz)
            art_grad.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 230))
            art_grad.setColorAt(1.0, QColor(max(0, ac.red() - 40), max(0, ac.green() - 40), max(0, ac.blue() - 40), 230))
            p.fillPath(art_path, QBrush(art_grad))
            p.setPen(QColor(255, 255, 255, 230))
            p.setFont(QFont("Segoe UI Emoji", 18))
            p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "♫")

        p.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(art_path)

        # 2. Title & Artist
        avail_t = bw - 88 - 140
        p.setPen(QColor(255, 255, 255, 245))
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        p.setFont(title_font)
        tfm = QFontMetrics(title_font)
        t_elided = tfm.elidedText(self._title, Qt.TextElideMode.ElideRight, int(avail_t))
        p.drawText(QRectF(88, 17, avail_t, 22), Qt.AlignmentFlag.AlignVCenter, t_elided)

        p.setPen(QColor(180, 180, 195, 190))
        artist_font = QFont("Segoe UI", 10)
        p.setFont(artist_font)
        afm = QFontMetrics(artist_font)
        a_elided = afm.elidedText(self._artist, Qt.TextElideMode.ElideRight, int(avail_t))
        p.drawText(QRectF(88, 41, avail_t, 18), Qt.AlignmentFlag.AlignVCenter, a_elided)

        # 3. Top-Right Icons: [🎤 Mic] [Equalizer] [Source Badge]
        right_x = bw - 20
        spot_x = right_x - 28
        p.setPen(Qt.PenStyle.NoPen)
        spot_color = QColor("#1DB954") if "spotify" in self._source.lower() else self._accent
        p.setBrush(spot_color)
        p.drawEllipse(QPointF(spot_x, 26), 8, 8)

        eq_x = spot_x - 24
        self._draw_equalizer_bars(p, eq_x - 20, 26, 20.0, 16.0)

        # Microphone Icon (Toggle Lyrics view)
        mic_x = eq_x - 30
        mic_active = (self._expanded_page == "lyrics")
        mic_color = self._accent if mic_active else QColor(255, 255, 255, 200)
        p.setPen(QPen(mic_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(mic_x - 3, 20, 6, 9), 3, 3)
        p.drawArc(QRectF(mic_x - 5, 22, 10, 8), 190 * 16, 160 * 16)
        p.drawLine(QPointF(mic_x, 30), QPointF(mic_x, 33))

        # 4. Middle Row: Slider or Synced Lyrics
        if self._expanded_page == "lyrics":
            self._draw_expanded_lyrics_view(p, bw, 86)
        else:
            self._draw_expanded_slider_view(p, bw, 86)

        # 5. Bottom Row: 3 Circular Glass Controls
        self._draw_expanded_controls(p, bw, 138)

    def _draw_expanded_slider_view(self, p: QPainter, bw: float, bar_y: float):
        pad_x = 22.0
        # Chevrons < and > on sides
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 160))
        p.drawText(QRectF(pad_x - 6, bar_y - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, "‹")
        p.drawText(QRectF(bw - pad_x - 10, bar_y - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, "›")

        p.setPen(QColor(160, 160, 175, 170))
        p.setFont(QFont("Segoe UI", 9))
        pos_s = self._pos_ms // 1000
        dur_s = self._dur_ms // 1000
        time_left = max(0, dur_s - pos_s)

        p.drawText(QRectF(pad_x + 14, bar_y - 8, 38, 16), Qt.AlignmentFlag.AlignLeft, f"{pos_s // 60}:{pos_s % 60:02d}")
        p.drawText(QRectF(bw - pad_x - 52, bar_y - 8, 38, 16), Qt.AlignmentFlag.AlignRight, f"-{time_left // 60}:{time_left % 60:02d}")

        slider_x = pad_x + 56
        slider_w = bw - (pad_x * 2) - 112
        track_h = 3.5
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 40))
        p.drawRoundedRect(QRectF(slider_x, bar_y - track_h / 2, slider_w, track_h), 1.8, 1.8)

        progress = min(1.0, max(0.0, self._pos_ms / self._dur_ms)) if self._dur_ms > 0 else 0.0
        fill_w = slider_w * progress
        p.setBrush(self._accent)
        p.drawRoundedRect(QRectF(slider_x, bar_y - track_h / 2, fill_w, track_h), 1.8, 1.8)

        # Scrubber Knob
        p.setBrush(QColor(255, 255, 255, 255))
        p.drawEllipse(QPointF(slider_x + fill_w, bar_y), 4.5, 4.5)

    def _draw_expanded_lyrics_view(self, p: QPainter, bw: float, top_y: float):
        pad = 26.0
        w = bw - (pad * 2)

        if self._lyric_prev_text:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(QColor(180, 180, 200, 90))
            p.drawText(QRectF(pad, top_y - 14, w, 12), Qt.AlignmentFlag.AlignCenter, self._lyric_prev_text)

        active_txt = self._lyric_text if self._lyric_text else "♪ Instrumental ♪"
        pill_rect = QRectF(pad + 10, top_y + 2, w - 20, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 75))
        p.drawRoundedRect(pill_rect, 11, 11)

        p.save()
        p.setOpacity(self._lyric_opacity)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 250))
        p.drawText(pill_rect, Qt.AlignmentFlag.AlignCenter, active_txt)
        p.restore()

        if self._lyric_next_text:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(QColor(180, 180, 200, 90))
            p.drawText(QRectF(pad, top_y + 28, w, 12), Qt.AlignmentFlag.AlignCenter, self._lyric_next_text)

    def _draw_expanded_controls(self, p: QPainter, bw: float, btn_y: float):
        cx = bw / 2
        ac = self._accent

        def draw_glass_btn(bx, by, br, is_center=False):
            g = QLinearGradient(bx - br, by - br, bx + br, by + br)
            if is_center:
                g.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 240))
                g.setColorAt(1.0, QColor(max(0, ac.red() - 40), max(0, ac.green() - 40), max(0, ac.blue() - 40), 240))
            else:
                g.setColorAt(0.0, QColor(42, 50, 60, 200))
                g.setColorAt(1.0, QColor(24, 30, 38, 200))
            p.setBrush(QBrush(g))
            p.setPen(QPen(QColor(255, 255, 255, 45), 1.0))
            p.drawEllipse(QPointF(bx, by), br, br)

        # Center Play/Pause button
        draw_glass_btn(cx, btn_y, 20, is_center=True)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 255))
        if self._is_playing:
            p.drawRoundedRect(QRectF(cx - 5.5, btn_y - 7, 3.5, 14), 1.5, 1.5)
            p.drawRoundedRect(QRectF(cx + 2.0, btn_y - 7, 3.5, 14), 1.5, 1.5)
        else:
            tri = QPainterPath()
            tri.moveTo(cx - 4.0, btn_y - 7.5)
            tri.lineTo(cx + 6.5, btn_y)
            tri.lineTo(cx - 4.0, btn_y + 7.5)
            tri.closeSubpath()
            p.fillPath(tri, QColor(255, 255, 255, 255))

        # Prev button
        prev_x = cx - 54
        draw_glass_btn(prev_x, btn_y, 17)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(prev_x - 7.0, btn_y - 5.5, 2.0, 11), 1, 1)
        t1 = QPainterPath()
        t1.moveTo(prev_x + 5.5, btn_y - 5.5)
        t1.lineTo(prev_x, btn_y)
        t1.lineTo(prev_x + 5.5, btn_y + 5.5)
        t1.closeSubpath()
        p.fillPath(t1, QColor(255, 255, 255, 240))

        # Next button
        next_x = cx + 54
        draw_glass_btn(next_x, btn_y, 17)
        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(next_x + 5.0, btn_y - 5.5, 2.0, 11), 1, 1)
        t2 = QPainterPath()
        t2.moveTo(next_x - 5.5, btn_y - 5.5)
        t2.lineTo(next_x, btn_y)
        t2.lineTo(next_x - 5.5, btn_y + 5.5)
        t2.closeSubpath()
        p.fillPath(t2, QColor(255, 255, 255, 240))

    # ─────────────────── Paint: Expanded Pomodoro ────────────────────────────

    def _paint_expanded_pomodoro(self, p: QPainter, bw: float, bh: float):
        # 1. Top Squircle Icon (Tomato) & Title
        art_sz = 52.0
        art_x = 22.0
        art_y = 16.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 12, 12)
        p.fillPath(art_path, QColor("#FF5722"))
        p.setFont(QFont("Segoe UI Emoji", 20))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "🍅")

        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRectF(88, 17, 240, 22), Qt.AlignmentFlag.AlignVCenter, "Pomodoro Timer")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(180, 180, 195, 190))
        phase_lbl = "Focus Session" if self.pomodoro_service.phase == "focus" else "Short Break"
        p.drawText(QRectF(88, 41, 240, 18), Qt.AlignmentFlag.AlignVCenter, f"{phase_lbl} • {self.pomodoro_service.focus_min} Min")

        # 2. Middle Row: Countdown Progress
        cx = bw / 2
        cy = 92.0
        r = 38.0
        pct = 1.0 - (self.pomodoro_service.seconds_left / max(1, self.pomodoro_service.total_seconds))
        
        p.setPen(QPen(QColor(255, 255, 255, 28), 5.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)

        ac = QColor("#FF5722") if self.pomodoro_service.phase == "focus" else QColor("#4CAF50")
        p.setPen(QPen(ac, 5.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 90 * 16, int(-pct * 360 * 16))

        mins = self.pomodoro_service.seconds_left // 60
        secs = self.pomodoro_service.seconds_left % 60
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 250))
        p.drawText(QRectF(cx - 50, cy - 14, 100, 28), Qt.AlignmentFlag.AlignCenter, f"{mins:02d}:{secs:02d}")

        # 3. Action Buttons [⏹ Reset]  [▶ Start / ⏸ Pause]  [⏭ Skip]
        btn_y = 142.0
        # Reset
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(cx - 85, btn_y - 14, 40, 28), 14, 14)
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(QRectF(cx - 85, btn_y - 14, 40, 28), Qt.AlignmentFlag.AlignCenter, "⏹")

        # Play/Pause
        p.setBrush(ac)
        p.drawRoundedRect(QRectF(cx - 38, btn_y - 15, 76, 30), 15, 15)
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 255))
        btn_lbl = "Pause" if self.pomodoro_service.is_running else "Start"
        p.drawText(QRectF(cx - 38, btn_y - 15, 76, 30), Qt.AlignmentFlag.AlignCenter, btn_lbl)

        # Skip
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(cx + 45, btn_y - 14, 40, 28), 14, 14)
        p.setFont(QFont("Segoe UI Emoji", 10))
        p.setPen(QColor(255, 255, 255, 220))
        p.drawText(QRectF(cx + 45, btn_y - 14, 40, 28), Qt.AlignmentFlag.AlignCenter, "⏭")

    # ─────────────────── Paint: Expanded Tasks ───────────────────────────────

    def _paint_expanded_tasks(self, p: QPainter, bw: float, bh: float):
        art_sz = 52.0
        art_x = 22.0
        art_y = 16.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 12, 12)
        p.fillPath(art_path, QColor("#3F51B5"))
        p.setFont(QFont("Segoe UI Emoji", 20))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "📋")

        tasks = self.task_service.get_tasks()
        remaining = sum(1 for t in tasks if not t.get("completed"))
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRectF(88, 17, 240, 22), Qt.AlignmentFlag.AlignVCenter, "Tasks & Reminders")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(180, 180, 195, 190))
        p.drawText(QRectF(88, 41, 240, 18), Qt.AlignmentFlag.AlignVCenter, f"{remaining} pending tasks")

        # 2-3 Task Items
        start_y = 74.0
        for i, t in enumerate(tasks[:2]):
            ty = start_y + (i * 28.0)
            is_done = t.get("completed", False)
            box_rect = QRectF(24, ty + 2, 16, 16)
            p.setPen(QPen(QColor(255, 255, 255, 180), 1.4))
            if is_done:
                p.setBrush(QColor("#4CAF50"))
                p.drawRoundedRect(box_rect, 8, 8)
                p.setPen(QColor(255, 255, 255, 255))
                p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                p.drawText(box_rect, Qt.AlignmentFlag.AlignCenter, "✓")
            else:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawRoundedRect(box_rect, 8, 8)

            font = QFont("Segoe UI", 9)
            font.setStrikeOut(is_done)
            p.setFont(font)
            p.setPen(QColor(180, 180, 190, 140) if is_done else QColor(255, 255, 255, 240))
            p.drawText(QRectF(50, ty, bw - 90, 20), Qt.AlignmentFlag.AlignVCenter, t.get("title"))

        if not tasks:
            p.setFont(QFont("Segoe UI", 9))
            p.setPen(QColor(180, 180, 190, 160))
            p.drawText(QRectF(24, 76, bw - 48, 20), Qt.AlignmentFlag.AlignLeft, "Tidak ada task. Tambahkan task baru di bawah.")

        # Bottom Actions: [+ Add Task] [Clear Done]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(63, 81, 181, 220))
        p.drawRoundedRect(QRectF(24, 138, 90, 26), 13, 13)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(24, 138, 90, 26), Qt.AlignmentFlag.AlignCenter, "+ Add Task")

        p.setBrush(QColor(255, 255, 255, 30))
        p.drawRoundedRect(QRectF(122, 138, 90, 26), 13, 13)
        p.setPen(QColor(220, 220, 230, 200))
        p.drawText(QRectF(122, 138, 90, 26), Qt.AlignmentFlag.AlignCenter, "Clear Done")

    # ─────────────────── Paint: Expanded Hydration ───────────────────────────

    def _paint_expanded_hydration(self, p: QPainter, bw: float, bh: float):
        art_sz = 52.0
        art_x = 22.0
        art_y = 16.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 12, 12)
        p.fillPath(art_path, QColor("#00BCD4"))
        p.setFont(QFont("Segoe UI Emoji", 20))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "💧")

        cur = self.hydration_service.current_l
        tgt = self.hydration_service.target_l
        pct = min(1.0, cur / max(0.1, tgt))

        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRectF(88, 17, 240, 22), Qt.AlignmentFlag.AlignVCenter, f"{cur:.2f} / {tgt:.1f} Liter Air")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(180, 180, 195, 190))
        p.drawText(QRectF(88, 41, 240, 18), Qt.AlignmentFlag.AlignVCenter, f"Target Harian ({int(pct * 100)}% tercapai)")

        # Progress bar
        bar_w = bw - 52
        bar_x = 26
        bar_y = 86
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, 8), 4, 4)
        p.setBrush(QColor("#00BCD4"))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w * pct, 8), 4, 4)

        # Quick Buttons
        cx = bw / 2
        btn_y = 138
        p.setBrush(QColor(0, 188, 212, 220))
        p.drawRoundedRect(QRectF(cx - 120, btn_y - 14, 72, 28), 14, 14)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(cx - 120, btn_y - 14, 72, 28), Qt.AlignmentFlag.AlignCenter, "+250 ml")

        p.drawRoundedRect(QRectF(cx - 36, btn_y - 14, 72, 28), 14, 14)
        p.drawText(QRectF(cx - 36, btn_y - 14, 72, 28), Qt.AlignmentFlag.AlignCenter, "+500 ml")

        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(cx + 48, btn_y - 14, 72, 28), 14, 14)
        p.drawText(QRectF(cx + 48, btn_y - 14, 72, 28), Qt.AlignmentFlag.AlignCenter, "Reset")

    # ─────────────────── Paint: Expanded Control Center ──────────────────────

    def _paint_expanded_control_center(self, p: QPainter, bw: float, bh: float):
        art_sz = 52.0
        art_x = 22.0
        art_y = 16.0
        art_path = QPainterPath()
        art_path.addRoundedRect(art_x, art_y, art_sz, art_sz, 12, 12)
        p.fillPath(art_path, QColor("#9C27B0"))
        p.setFont(QFont("Segoe UI Emoji", 20))
        p.setPen(QColor(255, 255, 255, 255))
        p.drawText(QRectF(art_x, art_y, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "🎛️")

        vol = self.system_service.get_volume()
        bat = self.system_service.get_battery_info()

        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 245))
        p.drawText(QRectF(88, 17, 240, 22), Qt.AlignmentFlag.AlignVCenter, f"Volume Master: {vol}%")

        p.setFont(QFont("Segoe UI", 10))
        p.setPen(QColor(180, 180, 195, 190))
        bat_str = f"🔋 Baterai: {bat['percent']}%" if bat.get("has_battery") else "⚡ Daya: Desktop AC"
        p.drawText(QRectF(88, 41, 240, 18), Qt.AlignmentFlag.AlignVCenter, bat_str)

        # Volume slider
        bar_x = 26.0
        bar_w = bw - 52.0
        bar_y = 86.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, 8), 4, 4)

        fill_w = bar_w * (vol / 100.0)
        p.setBrush(QColor("#9C27B0"))
        p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, 8), 4, 4)
        p.setBrush(QColor(255, 255, 255, 255))
        p.drawEllipse(QPointF(bar_x + fill_w, bar_y + 4), 6, 6)

        # Mute Action Button
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(26, 126, 95, 28), 14, 14)
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(QRectF(26, 126, 95, 28), Qt.AlignmentFlag.AlignCenter, "Mute Audio")

    # ─────────────────── Mouse & Hit Testing ─────────────────────────────────

    def _hit_test(self, pos: QPointF) -> str:
        bw = float(self.width())
        bh = float(self.height())

        if not self._is_expanded:
            return "body"

        # 1. Close '✕' button
        if QRectF(bw - 30, 14, 20, 20).contains(pos):
            return "close"

        # 2. Carousel Dots at bottom (click to jump to page)
        if (bh - 24) <= pos.y() <= bh:
            n = len(MODULE_LIST)
            spacing = 15.0
            start_x = (bw - ((n - 1) * spacing)) / 2.0
            for i in range(n):
                dx = start_x + (i * spacing)
                if abs(pos.x() - dx) <= 10:
                    return f"dot_{MODULE_LIST[i]}"

        # 3. Module Specific Hit Targets
        if self._active_module == "media":
            # Mic icon
            if QRectF(bw - 110, 18, 22, 22).contains(pos):
                return "mic"
            # Media buttons
            cx = bw / 2
            btn_y = 138.0
            if math.hypot(pos.x() - cx, pos.y() - btn_y) <= 22:
                return "play"
            if math.hypot(pos.x() - (cx - 54), pos.y() - btn_y) <= 19:
                return "prev"
            if math.hypot(pos.x() - (cx + 54), pos.y() - btn_y) <= 19:
                return "next"
            # Chevrons < and > on sides
            pad_x = 22.0
            bar_y = 86.0
            if QRectF(pad_x - 10, bar_y - 10, 24, 20).contains(pos):
                return "chevron_left"
            if QRectF(bw - pad_x - 14, bar_y - 10, 24, 20).contains(pos):
                return "chevron_right"
            # Slider
            slider_x = pad_x + 56
            slider_w = bw - (pad_x * 2) - 112
            if slider_x <= pos.x() <= slider_x + slider_w and 74 <= pos.y() <= 98:
                return "slider"

        elif self._active_module == "pomodoro":
            cx = bw / 2
            btn_y = 142.0
            if QRectF(cx - 85, btn_y - 14, 40, 28).contains(pos):
                return "pomo_reset"
            if QRectF(cx - 38, btn_y - 15, 76, 30).contains(pos):
                return "pomo_toggle"
            if QRectF(cx + 45, btn_y - 14, 40, 28).contains(pos):
                return "pomo_skip"

        elif self._active_module == "tasks":
            if QRectF(24, 138, 90, 26).contains(pos):
                return "task_add"
            if QRectF(122, 138, 90, 26).contains(pos):
                return "task_clear"
            start_y = 74.0
            for i in range(2):
                ty = start_y + (i * 28.0)
                if QRectF(20, ty, 28, 22).contains(pos):
                    return f"task_check_{i}"

        elif self._active_module == "hydration":
            cx = bw / 2
            btn_y = 138.0
            if QRectF(cx - 120, btn_y - 14, 72, 28).contains(pos):
                return "hydra_250"
            if QRectF(cx - 36, btn_y - 14, 72, 28).contains(pos):
                return "hydra_500"
            if QRectF(cx + 48, btn_y - 14, 72, 28).contains(pos):
                return "hydra_reset"

        elif self._active_module == "control_center":
            bar_x = 26.0
            bar_w = bw - 52.0
            if bar_x <= pos.x() <= bar_x + bar_w and 76 <= pos.y() <= 98:
                return "vol_slider"
            if QRectF(26, 126, 95, 28).contains(pos):
                return "vol_mute"

        return "body"

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self._swipe_start_pos = pos
            self._swipe_start_global = event.globalPosition()
            self._swipe_triggered = False
            target = self._hit_test(pos)

            if not self._is_expanded:
                self.expand()
                return

            if target == "close":
                self.collapse()
                return

            if target.startswith("dot_"):
                mod = target.replace("dot_", "")
                self.set_active_module(mod)
                return

            # Chevrons page cycle
            if target == "chevron_left":
                self.prev_module()
                return
            elif target == "chevron_right":
                self.next_module()
                return

            # Media Actions
            if target == "play":
                try:
                    self.media_service.play_pause()
                except Exception as e:
                    print(f"[NotchWindow] Play error: {e}")
                return
            elif target == "next":
                try:
                    self.media_service.skip_next()
                except Exception as e:
                    print(f"[NotchWindow] Next error: {e}")
                return
            elif target == "prev":
                try:
                    self.media_service.skip_previous()
                except Exception as e:
                    print(f"[NotchWindow] Prev error: {e}")
                return
            elif target == "mic":
                self._expanded_page = "lyrics" if self._expanded_page == "player" else "player"
                self.update()
                return
            elif target == "slider":
                pad_x = 22.0
                slider_x = pad_x + 56
                slider_w = float(self.width()) - (pad_x * 2) - 112
                click_ratio = max(0.0, min(1.0, (pos.x() - slider_x) / slider_w))
                self._pos_ms = int(click_ratio * self._dur_ms)
                try:
                    self.media_service.seek_to(self._pos_ms)
                except Exception as e:
                    print(f"[NotchWindow] Seek error: {e}")
                self.update()
                return

            # Pomodoro Actions
            elif target == "pomo_toggle":
                self.pomodoro_service.toggle()
                self.update()
                return
            elif target == "pomo_reset":
                self.pomodoro_service.reset()
                self.update()
                return
            elif target == "pomo_skip":
                self.pomodoro_service.skip_phase()
                self.update()
                return

            # Task Actions
            elif target == "task_add":
                text, ok = QInputDialog.getText(self, "Add New Task", "Deskripsi task:")
                if ok and text:
                    self.task_service.add_task(text)
                return
            elif target == "task_clear":
                self.task_service.clear_completed()
                return
            elif target.startswith("task_check_"):
                idx = int(target.replace("task_check_", ""))
                tasks = self.task_service.get_tasks()
                if idx < len(tasks):
                    self.task_service.toggle_task(tasks[idx]["id"])
                return

            # Hydration Actions
            elif target == "hydra_250":
                self.hydration_service.drink(0.25)
                return
            elif target == "hydra_500":
                self.hydration_service.drink(0.50)
                return
            elif target == "hydra_reset":
                self.hydration_service.reset()
                return

            # Control Center Actions
            elif target == "vol_slider":
                bar_x = 26.0
                bar_w = float(self.width()) - 52.0
                val = int(max(0.0, min(1.0, (pos.x() - bar_x) / bar_w)) * 100)
                self.system_service.set_volume(val)
                self.update()
                return
            elif target == "vol_mute":
                cur_vol = self.system_service.get_volume()
                new_vol = 0 if cur_vol > 0 else 50
                self.system_service.set_volume(new_vol)
                self.update()
                return

            # Drag window (Floating mode only)
            if self._layout_mode == "floating":
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_target = self._hover_target
        self._hover_target = self._hit_test(pos)

        if self._hover_target != old_target:
            if self._hover_target not in ("body", None):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

        # Swipe / Drag Detection using global coordinates
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_swipe_start_global") and self._swipe_start_global is not None:
            dx = event.globalPosition().x() - self._swipe_start_global.x()
            dy = event.globalPosition().y() - self._swipe_start_global.y()
            if abs(dx) > 35 and abs(dx) > abs(dy) * 1.2 and not self._swipe_triggered:
                self._swipe_triggered = True
                if dx < 0:
                    self.next_module()
                else:
                    self.prev_module()
                return

        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull() and self._hover_target == "body":
            if self._layout_mode == "floating" and not self._swipe_triggered:
                if not self._is_expanded or (event.modifiers() & Qt.KeyboardModifier.AltModifier):
                    self.move(event.globalPosition().toPoint() - self._drag_pos)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()
        self._swipe_start_pos = None
        self._swipe_start_global = None
        self._swipe_triggered = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        """Scroll wheel over island switches between modules smoothly."""
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta < 0:
            self.next_module()
        elif delta > 0:
            self.prev_module()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_expand()
        super().mouseDoubleClickEvent(event)

    def enterEvent(self, event):
        self.auto_collapse_timer.stop()
        if not self._is_expanded:
            self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_target = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()
        if self._is_expanded:
            delay = float(self.config.get("collapse_delay", 5.0))
            self.auto_collapse_timer.start(int(delay * 1000))
        super().leaveEvent(event)

    # ─────────────────── Right-Click Context Menu ─────────────────────────────

    def _show_context_menu(self, global_pos: QPoint):
        menu = RoundMenu(parent=self)

        mod_lbl = Action(f"🏝️ Notch v2.0 ({self._active_module.capitalize()})")
        mod_lbl.setEnabled(False)
        menu.addAction(mod_lbl)
        menu.addSeparator()

        # Switch Modules
        menu.addAction(Action("🎵 Media Player", triggered=lambda: self.set_active_module("media")))
        menu.addAction(Action("⏱️ Pomodoro Timer", triggered=lambda: self.set_active_module("pomodoro")))
        menu.addAction(Action("📋 Tasks & Notes", triggered=lambda: self.set_active_module("tasks")))
        menu.addAction(Action("💧 Hydration Tracker", triggered=lambda: self.set_active_module("hydration")))
        menu.addAction(Action("🎛️ Control Center", triggered=lambda: self.set_active_module("control_center")))

        menu.addSeparator()

        # Layout Mode Toggle
        is_anchored = (self._layout_mode == "anchored")
        layout_text = "📌 Switch to Floating Mode" if is_anchored else "📌 Switch to Anchored Mode"
        def toggle_layout():
            new_mode = "floating" if is_anchored else "anchored"
            self._layout_mode = new_mode
            self.config.set("layout_mode", new_mode)
            self._position_to_screen()
        menu.addAction(Action(layout_text, triggered=toggle_layout))

        # Theme Style Toggle
        is_glass = (self._theme_style == "liquid_glass")
        theme_text = "🖤 Switch to Obsidian Theme" if is_glass else "💎 Switch to Liquid Glass Theme"
        def toggle_theme():
            new_theme = "obsidian" if is_glass else "liquid_glass"
            self._theme_style = new_theme
            self.config.set("theme_style", new_theme)
            self.update()
        menu.addAction(Action(theme_text, triggered=toggle_theme))

        menu.addSeparator()
        menu.addAction(Action("⚙️ Settings...", triggered=self.open_settings_requested.emit))
        menu.addAction(Action("❌ Close / Exit", triggered=QApplication.instance().quit))

        menu.exec(global_pos)
