"""
NotchWindow — Dynamic Island for Windows
Faithful implementation of user design references:
- Expanded: Exact replica of Image 1 (squircle art, mic, eq bars, source badge, close 'x', progress line, 3 circular glass buttons, carousel dots, with switchable Lyrics page).
- Collapsed: Exact replica of Image 2 (organic notch hanging from top bezel with smooth concave flares, without eyes).
- Customizable Minimize Modes:
    1. 'minimal': Album Art + Sound Wave Bars only
    2. 'compact': Album Art + Title • Artist + Sound Wave Bars
    3. 'lyrics': Album Art + Live Synced Lyrics + Sound Wave Bars
"""

import math
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QRectF, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QPoint, QPointF, QSize
)
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient,
    QPainterPath, QFont, QFontMetrics, QPixmap, QCursor
)
from qframelesswindow import WindowEffect
from qfluentwidgets import RoundMenu, Action
from color_thief import extract_accent_color


# ─────────────────────────────────────────────────────────────────────────────
# Layout Constants
# ─────────────────────────────────────────────────────────────────────────────
EXPANDED_W     = 460
EXPANDED_H     = 185
EXPANDED_R     = 26.0

# Collapsed Widths based on mode
COLLAPSED_MIN_W    = 200
COLLAPSED_COMPACT_W = 320
COLLAPSED_LYRIC_W  = 420
COLLAPSED_H        = 38

ANIM_MS = 280


class NotchWindow(QWidget):
    open_settings_requested = pyqtSignal()

    def __init__(self, config, media_service, lyrics_engine):
        super().__init__()
        self.config        = config
        self.media_service = media_service
        self.lyrics_engine = lyrics_engine

        # Frameless, Always on Top, Hidden from Alt+Tab
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        # State
        self._is_expanded    = False
        self._expanded_page  = "player"  # "player" or "lyrics"
        self._drag_pos       = QPoint()
        self._accent         = QColor(config.get("custom_accent", "#1DB954"))
        self._lyrics         = []
        self._lyric_idx      = -1
        self._wave_step      = 0.0
        self._pixmap         = None
        self._title          = "Notch"
        self._artist         = "No track playing"
        self._is_playing     = False
        self._pos_ms         = 0
        self._dur_ms         = 0
        self._source         = "Spotify"
        self._lyric_text     = ""
        self._lyric_prev_text = ""
        self._lyric_next_text = ""
        self._lyric_opacity  = 1.0

        # Collapsed Mode: "minimal", "compact", "lyrics"
        self._collapsed_mode = self.config.get("collapsed_mode", "compact")

        # Interactive hit testing hover target
        self._hover_target = None
        self.setMouseTracking(True)

        # Window geometry values
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

        # Lyric fade-in transition
        self._lyric_anim_step = 0
        self.lyric_fade_timer = QTimer(self)
        self.lyric_fade_timer.setInterval(16)
        self.lyric_fade_timer.timeout.connect(self._on_lyric_fade)

        self._connect_signals()
        self._position_to_screen()

    # ─────────────────── DWM Blur Behind ─────────────────────────────────────

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(50, self._apply_blur)

    def _apply_blur(self):
        try:
            effect = WindowEffect(self)
            effect.enableBlurBehindWindow(int(self.winId()))
        except Exception:
            pass

    # ─────────────────── Geometry Helpers ────────────────────────────────────

    def _get_collapsed_w(self) -> int:
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

    def _position_to_screen(self):
        w = EXPANDED_W if self._is_expanded else self._get_collapsed_w()
        h = EXPANDED_H if self._is_expanded else COLLAPSED_H
        self._curr_w = w
        self._curr_h = h
        x = self._screen_center_x(w)
        # Flush at top edge y=0
        self.setGeometry(x, 0, w, h)
        self.update()

    def apply_geometry_from_config(self):
        self._collapsed_mode = self.config.get("collapsed_mode", "compact")
        self._position_to_screen()

    # ─────────────────── Signals ─────────────────────────────────────────────

    def _connect_signals(self):
        self.media_service.track_changed.connect(self._on_track_changed)
        self.media_service.position_ticked.connect(self._on_position_ticked)
        self.media_service.playback_state_changed.connect(self._on_playback_state_changed)

    # ─────────────────── Media Callbacks ─────────────────────────────────────

    def _on_track_changed(self, track: dict):
        self._title   = track.get("title", "No Track")
        self._artist  = track.get("artist", "")
        self._dur_ms  = track.get("duration_ms", 0)
        self._source  = track.get("source", "Spotify")
        pixmap        = track.get("pixmap")

        self._pixmap = pixmap if (pixmap and not pixmap.isNull()) else None

        if self.config.get("auto_accent", True):
            self._accent = extract_accent_color(pixmap, self.config.get("custom_accent", "#1DB954"))
        else:
            self._accent = QColor(self.config.get("custom_accent", "#1DB954"))

        total_sec = self._dur_ms // 1000
        if self._title and self._title != "No Track Playing":
            self._lyrics          = self.lyrics_engine.fetch_lyrics(self._title, self._artist, total_sec)
            self._lyric_idx       = -1
            self._lyric_text      = ""
            self._lyric_prev_text = ""
            self._lyric_next_text = ""
        else:
            self._lyrics = []

        if self.config.get("auto_expand_on_new_song", True) and self._title != "No Track Playing":
            self.expand()
            delay = float(self.config.get("collapse_delay", 5.0))
            self.auto_collapse_timer.start(int(delay * 1000))

        self.update()

    def _on_position_ticked(self, pos_ms: int):
        self._pos_ms = pos_ms
        self._update_lyric(pos_ms)
        self.update()

    def _on_playback_state_changed(self, is_playing: bool):
        self._is_playing = is_playing
        self.update()

    def _on_tick(self):
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

    def set_collapsed_mode(self, mode: str):
        self._collapsed_mode = mode
        self.config.set("collapsed_mode", mode)
        if not self._is_expanded:
            self._animate_to(self._get_collapsed_w(), COLLAPSED_H)
        self.update()

    def _animate_to(self, target_w: int, target_h: int):
        x = self._screen_center_x(target_w)
        end_rect = QRect(x, 0, target_w, target_h)
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
        if not self.underMouse():
            self.collapse()

    # ─────────────────── Painting ────────────────────────────────────────────

    def _create_collapsed_notch_path(self, w: float, h: float) -> QPainterPath:
        """
        Exact shape of Image 2 (organic notch hanging from top bezel):
        Starts at (0,0), curves smoothly inward with a concave flare,
        drops down, rounds the bottom corners, and mirrors to (w,0).
        """
        flare_w = 28.0
        flare_h = 18.0
        r = 16.0
        path = QPainterPath()
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
        return path

    def _create_expanded_card_path(self, w: float, h: float) -> QPainterPath:
        """Exact shape of Image 1 (sleek card with rounded corners r=26)."""
        path = QPainterPath()
        path.addRoundedRect(0, 0, w, h, EXPANDED_R, EXPANDED_R)
        return path

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        bw = float(self.width())
        bh = float(self.height())

        if self._is_expanded:
            self._paint_expanded(p, bw, bh)
        else:
            self._paint_collapsed(p, bw, bh)

        p.end()

    # ─────────────────── Paint Collapsed (Image 2 Replica) ───────────────────

    def _paint_collapsed(self, p: QPainter, bw: float, bh: float):
        path = self._create_collapsed_notch_path(bw, bh)

        # Translucent dark obsidian glass base (85% alpha)
        p.fillPath(path, QColor(8, 10, 14, 235))

        # Thin 1px border
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        flare_w = 28.0

        # 1. Left Squircle Album Photo (24x24, r=6)
        art_sz = 24.0
        art_x = flare_w + 6.0
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

        # 2. Right Animated Sound Wave Bars (4 bars)
        wave_w = 26.0
        wave_right = bw - flare_w - 6.0
        wave_x = wave_right - wave_w
        self._draw_equalizer_bars(p, wave_x, bh / 2, wave_w, 16.0)

        # 3. Middle Content depending on Collapsed Mode
        content_left = art_x + art_sz + 8.0
        content_w = wave_x - content_left - 8.0

        if self._collapsed_mode == "minimal":
            # Mode A: Only Art + Waveform (Super compact)
            pass

        elif self._collapsed_mode == "compact":
            # Mode B: Art + Title • Artist + Waveform
            if content_w > 20:
                p.setPen(QColor(255, 255, 255, 240))
                font = QFont("Segoe UI", 9, QFont.Weight.Bold)
                p.setFont(font)
                fm = QFontMetrics(font)
                text = f"{self._title} • {self._artist}" if self._artist else self._title
                elided = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(content_w))
                p.drawText(QRectF(content_left, 0, content_w, bh), Qt.AlignmentFlag.AlignVCenter, elided)

        elif self._collapsed_mode == "lyrics":
            # Mode C: Art + Live Synced Lyric + Waveform
            if content_w > 20:
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

    # ─────────────────── Paint Expanded (Image 1 Replica) ───────────────────

    def _paint_expanded(self, p: QPainter, bw: float, bh: float):
        card = self._create_expanded_card_path(bw, bh)

        # Dark obsidian base (90% alpha)
        p.fillPath(card, QColor(10, 12, 16, 235))

        # Dynamic Ambient Radial Glow at bottom-center (like Image 1 green/purple glow)
        ac = self._accent
        glow = QRadialGradient(bw * 0.45, bh * 0.85, bw * 0.58)
        glow.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 135))
        glow.setColorAt(0.5, QColor(ac.red(), ac.green(), ac.blue(), 45))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.fillPath(card, QBrush(glow))

        # 1px border
        p.setPen(QPen(QColor(255, 255, 255, 26), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(card)

        # ── TOP ROW ──────────────────────────────────────────────────────────
        # 1. Squircle Album Art (50x50, r=12)
        art_sz = 50.0
        art_path = QPainterPath()
        art_path.addRoundedRect(18, 16, art_sz, art_sz, 12, 12)

        if self._pixmap:
            p.save()
            p.setClipPath(art_path)
            scaled = self._pixmap.scaled(
                int(art_sz), int(art_sz),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            p.drawPixmap(18, 16, scaled)
            p.restore()
        else:
            art_grad = QLinearGradient(18, 16, 18 + art_sz, 16 + art_sz)
            art_grad.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), 230))
            art_grad.setColorAt(1.0, QColor(max(0, ac.red() - 40), max(0, ac.green() - 40), max(0, ac.blue() - 40), 230))
            p.fillPath(art_path, QBrush(art_grad))
            p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
            p.drawPath(art_path)
            p.setPen(QColor(255, 255, 255, 230))
            p.setFont(QFont("Segoe UI Emoji", 18))
            p.drawText(QRectF(18, 16, art_sz, art_sz), Qt.AlignmentFlag.AlignCenter, "♫")

        p.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(art_path)

        # 2. Title & Artist Text
        p.setPen(QColor(255, 255, 255, 245))
        title_font = QFont("Segoe UI", 12, QFont.Weight.Bold)
        p.setFont(title_font)
        tfm = QFontMetrics(title_font)
        avail_t = bw - 80 - 150
        t_elided = tfm.elidedText(self._title, Qt.TextElideMode.ElideRight, int(avail_t))
        p.drawText(QRectF(80, 17, avail_t, 22), Qt.AlignmentFlag.AlignVCenter, t_elided)

        p.setPen(QColor(180, 180, 195, 190))
        artist_font = QFont("Segoe UI", 10)
        p.setFont(artist_font)
        afm = QFontMetrics(artist_font)
        a_elided = afm.elidedText(self._artist, Qt.TextElideMode.ElideRight, int(avail_t))
        p.drawText(QRectF(80, 41, avail_t, 18), Qt.AlignmentFlag.AlignVCenter, a_elided)

        # 3. Top-Right Icons: [🎤 Mic] [Equalizer] [Source Badge] [✕ Close]
        right_x = bw - 20

        # Close '✕'
        close_hover = (self._hover_target == "close")
        close_alpha = 245 if close_hover else 180
        p.setPen(QPen(QColor(255, 255, 255, close_alpha), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(right_x - 10, 25), QPointF(right_x - 2, 33))
        p.drawLine(QPointF(right_x - 2, 25), QPointF(right_x - 10, 33))

        # Source Badge (Spotify circle or YT Music)
        spot_x = right_x - 28
        p.setPen(Qt.PenStyle.NoPen)
        spot_color = QColor("#1DB954") if "spotify" in self._source.lower() else self._accent
        p.setBrush(spot_color)
        p.drawEllipse(QPointF(spot_x, 29), 8, 8)
        p.setPen(QPen(QColor(0, 0, 0, 220), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(QRectF(spot_x - 5, 25, 10, 8), 45 * 16, 90 * 16)
        p.drawArc(QRectF(spot_x - 4, 27.5, 8, 6), 45 * 16, 90 * 16)

        # 4-bar Dynamic Equalizer
        eq_x = spot_x - 24
        self._draw_equalizer_bars(p, eq_x - 20, 29, 20.0, 16.0)

        # Microphone Icon (Clickable: Toggles between Player view and Lyrics view!)
        mic_x = eq_x - 30
        mic_hover = (self._hover_target == "mic")
        mic_active = (self._expanded_page == "lyrics")
        mic_color = ac if mic_active else (QColor(255, 255, 255, 245) if mic_hover else QColor(255, 255, 255, 180))
        p.setPen(QPen(mic_color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(mic_x - 3, 23, 6, 9), 3, 3)
        p.drawArc(QRectF(mic_x - 5, 25, 10, 8), 190 * 16, 160 * 16)
        p.drawLine(QPointF(mic_x, 33), QPointF(mic_x, 36))

        # ── MIDDLE ROW ───────────────────────────────────────────────────────
        if self._expanded_page == "lyrics":
            # LYRICS VIEW (3 Lines of Live Synced Lyrics)
            self._draw_expanded_lyrics_view(p, bw, 84)
        else:
            # PLAYER VIEW (Slider with Chevron Left/Right as in Image 1)
            self._draw_expanded_slider_view(p, bw, 84)

        # ── BOTTOM ROW ───────────────────────────────────────────────────────
        # 3 Circular Glass Buttons: [⏮]  [▶ / ⏸]  [⏭]
        self._draw_expanded_controls(p, bw, 138)

        # Carousel Dots at Very Bottom
        self._draw_carousel_dots(p, bw, bh - 10)

    def _draw_equalizer_bars(self, p: QPainter, x: float, cy: float, w: float, h: float):
        num_bars = 4
        bar_w = 2.5
        gap = (w - (num_bars * bar_w)) / (num_bars - 1)
        # Vibrant green like Image 1 or dynamic accent
        bar_color = QColor("#1DB954") if "spotify" in self._source.lower() else self._accent

        for i in range(num_bars):
            phase = self._wave_step * 1.5 + i * 0.9
            if self._is_playing:
                bar_h = max(4.0, (math.sin(phase) * 0.5 + 0.5) * h)
                alpha = int(220 + 35 * math.sin(phase))
            else:
                bar_h = 5.0
                alpha = 180

            bx = x + i * (bar_w + gap)
            by = cy - bar_h / 2
            p.setBrush(QColor(bar_color.red(), bar_color.green(), bar_color.blue(), alpha))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), bar_w / 2, bar_w / 2)

    def _draw_expanded_slider_view(self, p: QPainter, bw: float, bar_y: float):
        """Slider row matching Image 1: `<` 1:28 [====] -2:03 `>`"""
        pad_x = 24.0

        # Left Chevron `<`
        p.setPen(QPen(QColor(255, 255, 255, 140), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(pad_x + 2, bar_y - 2), QPointF(pad_x - 2, bar_y + 2))
        p.drawLine(QPointF(pad_x - 2, bar_y + 2), QPointF(pad_x + 2, bar_y + 6))

        # Right Chevron `>`
        p.drawLine(QPointF(bw - pad_x - 2, bar_y - 2), QPointF(bw - pad_x + 2, bar_y + 2))
        p.drawLine(QPointF(bw - pad_x + 2, bar_y + 2), QPointF(bw - pad_x - 2, bar_y + 6))

        # Timestamps
        cur_s = self._pos_ms // 1000
        tot_s = self._dur_ms // 1000
        rem_s = max(0, tot_s - cur_s)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor(180, 180, 195, 170))
        p.drawText(QRectF(pad_x + 12, bar_y - 5, 36, 14), Qt.AlignmentFlag.AlignLeft, f"{cur_s // 60}:{cur_s % 60:02d}")
        p.drawText(QRectF(bw - pad_x - 48, bar_y - 5, 36, 14), Qt.AlignmentFlag.AlignRight, f"-{rem_s // 60}:{rem_s % 60:02d}")

        # Progress Track
        slider_x = pad_x + 52
        slider_w = bw - (pad_x * 2) - 104
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 35))
        p.drawRoundedRect(QRectF(slider_x, bar_y + 1, slider_w, 3), 1.5, 1.5)

        # Progress Fill (Accent color)
        ratio = max(0.0, min(1.0, self._pos_ms / max(1, self._dur_ms)))
        fill_w = slider_w * ratio
        if fill_w > 0:
            p.setBrush(self._accent)
            p.drawRoundedRect(QRectF(slider_x, bar_y + 1, fill_w, 3), 1.5, 1.5)

    def _draw_expanded_lyrics_view(self, p: QPainter, bw: float, top_y: float):
        """Lyrics page with illuminated active lyric capsule."""
        pad = 24.0
        w = bw - pad * 2

        p.save()
        p.setOpacity(self._lyric_opacity)

        capsule_h = 24.0
        capsule_y = top_y - 4

        # Active lyric subtle capsule
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 16))
        p.drawRoundedRect(QRectF(pad + 8, capsule_y, w - 16, capsule_h), 6, 6)

        # Active line text
        lyric = self._lyric_text if self._lyric_text else "Waiting for synced lyrics..."
        p.setPen(QColor(255, 255, 255, 245))
        p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        p.drawText(QRectF(pad + 12, capsule_y, w - 24, capsule_h),
                   Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, lyric)

        # Previous Line
        if self._lyric_prev_text:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(QColor(180, 180, 200, 90))
            p.drawText(QRectF(pad, top_y - 18, w, 12), Qt.AlignmentFlag.AlignCenter, self._lyric_prev_text)

        # Next Line
        if self._lyric_next_text:
            p.setFont(QFont("Segoe UI", 8))
            p.setPen(QColor(180, 180, 200, 90))
            p.drawText(QRectF(pad, top_y + 24, w, 12), Qt.AlignmentFlag.AlignCenter, self._lyric_next_text)

        p.restore()

    def _draw_expanded_controls(self, p: QPainter, bw: float, btn_y: float):
        """3 Circular Glass Action Buttons matching Image 1: [⏮]  [▶ / ⏸]  [⏭]"""
        cx = bw / 2
        cy = btn_y
        ac = self._accent

        # Helper for circular glass button
        def draw_glass_btn(bx, by, br, is_center=False, is_hover=False):
            if is_center:
                g = QLinearGradient(bx - br, by - br, bx + br, by + br)
                alpha = 255 if is_hover else 230
                g.setColorAt(0.0, QColor(ac.red(), ac.green(), ac.blue(), alpha))
                g.setColorAt(1.0, QColor(max(0, ac.red() - 40), max(0, ac.green() - 40), max(0, ac.blue() - 40), alpha))
                p.setBrush(QBrush(g))
            else:
                g = QLinearGradient(bx - br, by - br, bx + br, by + br)
                bg_alpha = 230 if is_hover else 190
                g.setColorAt(0.0, QColor(42, 50, 48, bg_alpha))
                g.setColorAt(1.0, QColor(24, 30, 28, bg_alpha))
                p.setBrush(QBrush(g))

            border_alpha = 60 if is_hover else 30
            p.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.0))
            p.drawEllipse(QPointF(bx, by), br, br)

        # Center Play/Pause button (r=20)
        play_hover = (self._hover_target == "play")
        draw_glass_btn(cx, btn_y, 20, is_center=True, is_hover=play_hover)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 255))
        if self._is_playing:
            # Pause bars
            p.drawRoundedRect(QRectF(cx - 5, btn_y - 7, 3.5, 14), 1.5, 1.5)
            p.drawRoundedRect(QRectF(cx + 1.5, btn_y - 7, 3.5, 14), 1.5, 1.5)
        else:
            # Play triangle
            tri = QPainterPath()
            tri.moveTo(cx - 3.5, cy - 7.0)
            tri.lineTo(cx + 6.0, cy)
            tri.lineTo(cx - 3.5, cy + 7.0)
            tri.closeSubpath()
            p.fillPath(tri, QColor(255, 255, 255, 255))

        # Prev button (r=17)
        prev_hover = (self._hover_target == "prev")
        prev_x = cx - 54
        draw_glass_btn(prev_x, btn_y, 17, is_hover=prev_hover)

        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(prev_x - 6.5, btn_y - 5.5, 2.0, 11), 1, 1)
        t1 = QPainterPath()
        t1.moveTo(prev_x + 5.5, btn_y - 5.5)
        t1.lineTo(prev_x, btn_y)
        t1.lineTo(prev_x + 5.5, btn_y + 5.5)
        t1.closeSubpath()
        p.fillPath(t1, QColor(255, 255, 255, 240))
        t2 = QPainterPath()
        t2.moveTo(prev_x, btn_y - 5.5)
        t2.lineTo(prev_x - 5.5, btn_y)
        t2.lineTo(prev_x, btn_y + 5.5)
        t2.closeSubpath()
        p.fillPath(t2, QColor(255, 255, 255, 240))

        # Next button (r=17)
        next_hover = (self._hover_target == "next")
        next_x = cx + 54
        draw_glass_btn(next_x, btn_y, 17, is_hover=next_hover)

        p.setBrush(QColor(255, 255, 255, 240))
        p.drawRoundedRect(QRectF(next_x + 4.5, btn_y - 5.5, 2.0, 11), 1, 1)
        t3 = QPainterPath()
        t3.moveTo(next_x - 5.5, btn_y - 5.5)
        t3.lineTo(next_x, btn_y)
        t3.lineTo(next_x - 5.5, btn_y + 5.5)
        t3.closeSubpath()
        p.fillPath(t3, QColor(255, 255, 255, 240))
        t4 = QPainterPath()
        t4.moveTo(next_x, btn_y - 5.5)
        t4.lineTo(next_x + 5.5, btn_y)
        t4.lineTo(next_x, btn_y + 5.5)
        t4.closeSubpath()
        p.fillPath(t4, QColor(255, 255, 255, 240))

    def _draw_carousel_dots(self, p: QPainter, bw: float, dot_y: float):
        """Carousel dots at bottom center (Image 1 replica)."""
        cx = bw / 2
        dots_x = cx - 24
        is_lyrics = (self._expanded_page == "lyrics")

        for d in range(7):
            dx = dots_x + d * 8
            p.setPen(Qt.PenStyle.NoPen)
            # Active dot
            if (not is_lyrics and d == 1) or (is_lyrics and d == 2):
                p.setBrush(QColor(255, 255, 255, 230))
                p.drawRoundedRect(QRectF(dx - 3, dot_y - 1.5, 8, 3), 1.5, 1.5)
            else:
                p.setBrush(QColor(255, 255, 255, 75))
                p.drawEllipse(QPointF(dx, dot_y), 1.5, 1.5)

    # ─────────────────── Mouse & Hit Testing ─────────────────────────────────

    def _hit_test(self, pos: QPointF):
        bw = float(self.width())
        bh = float(self.height())

        if not self._is_expanded:
            return "body"

        # Expanded state targets:
        # 1. Close '✕'
        right_x = bw - 20
        if QRectF(right_x - 14, 20, 20, 20).contains(pos):
            return "close"

        # 2. Mic Icon
        spot_x = right_x - 28
        eq_x = spot_x - 24
        mic_x = eq_x - 30
        if QRectF(mic_x - 8, 20, 16, 20).contains(pos):
            return "mic"

        # 3. Controls (Play, Prev, Next)
        btn_y = 138.0
        cx = bw / 2
        if math.hypot(pos.x() - cx, pos.y() - btn_y) <= 22:
            return "play"
        if math.hypot(pos.x() - (cx - 54), pos.y() - btn_y) <= 19:
            return "prev"
        if math.hypot(pos.x() - (cx + 54), pos.y() - btn_y) <= 19:
            return "next"

        # 4. Progress Slider / Chevrons
        bar_y = 84.0
        pad_x = 24.0
        if QRectF(pad_x - 8, bar_y - 8, 20, 20).contains(pos):
            return "chevron_left"
        if QRectF(bw - pad_x - 12, bar_y - 8, 20, 20).contains(pos):
            return "chevron_right"

        slider_x = pad_x + 52
        slider_w = bw - (pad_x * 2) - 104
        if slider_x <= pos.x() <= slider_x + slider_w and (bar_y - 6) <= pos.y() <= (bar_y + 10):
            return "slider"

        # 5. Carousel dots
        if (bh - 18) <= pos.y() <= bh:
            return "dots"

        return "body"

    def mouseMoveEvent(self, event):
        pos = event.position()
        old_target = self._hover_target
        self._hover_target = self._hit_test(pos)

        if self._hover_target != old_target:
            if self._hover_target in ("close", "mic", "play", "prev", "next", "slider", "chevron_left", "chevron_right", "dots"):
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull() and self._hover_target == "body":
            self.move(event.globalPosition().toPoint() - self._drag_pos)

        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            target = self._hit_test(pos)

            if not self._is_expanded:
                # Clicking collapsed notch expands it!
                self.expand()
                return

            if target == "close":
                self.collapse()
                return
            elif target == "mic":
                # Toggle Player vs Lyrics view
                self._expanded_page = "lyrics" if self._expanded_page == "player" else "player"
                self.update()
                return
            elif target in ("chevron_left", "chevron_right", "dots"):
                # Toggle page
                self._expanded_page = "lyrics" if self._expanded_page == "player" else "player"
                self.update()
                return
            elif target == "play":
                self.media_service.play_pause()
                return
            elif target == "next":
                self.media_service.skip_next()
                return
            elif target == "prev":
                self.media_service.skip_previous()
                return
            elif target == "slider":
                pad_x = 24.0
                slider_x = pad_x + 52
                slider_w = float(self.width()) - (pad_x * 2) - 104
                click_ratio = max(0.0, min(1.0, (pos.x() - slider_x) / slider_w))
                self._pos_ms = int(click_ratio * self._dur_ms)
                self.update()
                return

            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

        super().mousePressEvent(event)

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
            delay = float(self.config.get("collapse_delay", 4.0))
            self.auto_collapse_timer.start(int(delay * 1000))
        super().leaveEvent(event)

    # ─────────────────── Right-Click Context Menu ────────────────────────────

    def _show_context_menu(self, global_pos: QPoint):
        menu = RoundMenu(parent=self)

        expand_label = "▲ Lipat Notch (Minimize)" if self._is_expanded else "▼ Buka Notch (Expand)"
        action_toggle = Action(expand_label)
        action_toggle.triggered.connect(self.toggle_expand)
        menu.addAction(action_toggle)

        menu.addSeparator()

        # Collapsed Mode Customization
        sub_title = Action("📌 Tampilan Minimize:")
        sub_title.setEnabled(False)
        menu.addAction(sub_title)

        act_m1 = Action("  1. Foto Album & Animasi Suara" + (" ✓" if self._collapsed_mode == "minimal" else ""))
        act_m1.triggered.connect(lambda: self.set_collapsed_mode("minimal"))
        menu.addAction(act_m1)

        act_m2 = Action("  2. Foto, Judul & Animasi Suara" + (" ✓" if self._collapsed_mode == "compact" else ""))
        act_m2.triggered.connect(lambda: self.set_collapsed_mode("compact"))
        menu.addAction(act_m2)

        act_m3 = Action("  3. Foto, Lirik Berjalan & Animasi" + (" ✓" if self._collapsed_mode == "lyrics" else ""))
        act_m3.triggered.connect(lambda: self.set_collapsed_mode("lyrics"))
        menu.addAction(act_m3)

        menu.addSeparator()

        action_settings = Action("⚙ Pengaturan Lengkap...")
        action_settings.triggered.connect(self.open_settings_requested.emit)
        menu.addAction(action_settings)

        action_quit = Action("❌ Keluar dari Notch")
        action_quit.triggered.connect(QApplication.instance().quit)
        menu.addAction(action_quit)

        menu.exec(global_pos)
