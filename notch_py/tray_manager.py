from PyQt6.QtWidgets import QSystemTrayIcon, QApplication, QMessageBox
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QPoint, QRectF
from qfluentwidgets import RoundMenu, Action

class TrayManager:
    def __init__(self, notch_window, settings_dialog, media_service):
        self.notch_window = notch_window
        self.settings_dialog = settings_dialog
        self.media_service = media_service

        self.tray_icon = QSystemTrayIcon(self._generate_icon(), notch_window)
        self.tray_icon.setToolTip("Notch Dynamic Island")

        self._build_menu()

        self.tray_icon.activated.connect(self._on_tray_activated)
        self.media_service.track_changed.connect(self._on_track_changed)
        self.tray_icon.show()
        # Toast notification to alert user that Notch is running
        try:
            self.tray_icon.showMessage(
                "Notch Dynamic Island",
                "Notch sudah berjalan! Lihat bagian atas tengah layar Anda 🎵",
                QSystemTrayIcon.MessageIcon.Information,
                3500
            )
        except Exception:
            pass

    def _generate_icon(self) -> QIcon:
        pix = QPixmap(32, 32)
        pix.fill(Qt.GlobalColor.transparent)

        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded pill
        path = QPainterPath()
        path.addRoundedRect(QRectF(2, 8, 28, 16), 8, 8)
        p.fillPath(path, QBrush(QColor(18, 18, 24)))
        p.setPen(QPen(QColor(59, 130, 246), 1.5))
        p.drawPath(path)

        # Draw mini accent dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(30, 215, 96)))
        p.drawEllipse(7, 13, 5, 5)

        # Mini equalizers
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawRect(16, 14, 2, 5)
        p.drawRect(20, 11, 2, 8)
        p.drawRect(24, 13, 2, 6)

        p.end()
        return QIcon(pix)

    def _build_menu(self):
        self.menu = RoundMenu(parent=self.notch_window)

        self.header_action = Action("🎵 No track playing")
        self.header_action.setEnabled(False)
        self.menu.addAction(self.header_action)

        self.menu.addSeparator()

        self.play_action = Action("⏯ Play / Pause")
        self.play_action.triggered.connect(self.media_service.play_pause)
        self.menu.addAction(self.play_action)

        next_action = Action("⏭ Next Track")
        next_action.triggered.connect(self.media_service.skip_next)
        self.menu.addAction(next_action)

        prev_action = Action("⏮ Previous Track")
        prev_action.triggered.connect(self.media_service.skip_previous)
        self.menu.addAction(prev_action)

        self.menu.addSeparator()

        # Modules Submenu / Quick Selector
        self.menu.addAction(Action("🎵 Switch to Media Player", triggered=lambda: self.notch_window.set_active_module("media")))
        self.menu.addAction(Action("⏱️ Switch to Pomodoro Timer", triggered=lambda: self.notch_window.set_active_module("pomodoro")))
        self.menu.addAction(Action("📋 Switch to Tasks & Reminders", triggered=lambda: self.notch_window.set_active_module("tasks")))
        self.menu.addAction(Action("💧 Switch to Hydration Tracker", triggered=lambda: self.notch_window.set_active_module("hydration")))
        self.menu.addAction(Action("🎛️ Switch to Control Center", triggered=lambda: self.notch_window.set_active_module("control_center")))

        self.menu.addSeparator()

        toggle_action = Action("👁 Toggle Notch Overlay")
        toggle_action.triggered.connect(self._toggle_notch)
        self.menu.addAction(toggle_action)

        settings_action = Action("⚙ Settings...")
        settings_action.triggered.connect(self._show_settings)
        self.menu.addAction(settings_action)

        about_action = Action("ℹ About Notch")
        about_action.triggered.connect(self._show_about)
        self.menu.addAction(about_action)

        self.menu.addSeparator()

        quit_action = Action("❌ Exit Notch")
        quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(quit_action)

        self.tray_icon.setContextMenu(self.menu)

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.notch_window.isVisible():
                self.notch_window.toggle_expand()
            else:
                self.notch_window.show()
                self.notch_window.expand()

    def _toggle_notch(self):
        if self.notch_window.isVisible():
            self.notch_window.hide()
        else:
            self.notch_window.show()
            self.notch_window.expand()

    def _show_settings(self):
        self.settings_dialog.show()
        self.settings_dialog.activateWindow()

    def _show_about(self):
        QMessageBox.information(
            self.notch_window,
            "About Notch",
            "Notch — Dynamic Island for Windows\n\n"
            "Built with PyQt6, PyQt-Fluent-Widgets, and Windows DWM Acrylic Blur Behind.\n"
            "Displays real-time synced lyrics & playback from YouTube Music and Spotify.\n\n"
            "Version 1.0.0 (Liquid Glass Edition)"
        )

    def _on_track_changed(self, track):
        title = track.get("title", "No track playing")
        artist = track.get("artist", "")
        if title != "No Track Playing":
            self.tray_icon.setToolTip(f"Notch — {title} by {artist}")
            self.header_action.setText(f"🎵 {title} • {artist}")
        else:
            self.tray_icon.setToolTip("Notch Dynamic Island")
            self.header_action.setText("🎵 No track playing")
