import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config import Config
from lyrics_engine import LyricsEngine
from media_service import MediaService
from notch_window import NotchWindow
from settings_dialog import SettingsDialog
from tray_manager import TrayManager


def enforce_single_instance():
    mutex_name = "Global\\NotchDynamicIsland_Python_SingleInstance"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    ERROR_ALREADY_EXISTS = 183
    if last_error == ERROR_ALREADY_EXISTS:
        return None
    return mutex


def main():
    mutex = enforce_single_instance()
    if not mutex:
        print("Notch is already running in the system tray.")
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config        = Config()
    lyrics_engine = LyricsEngine()
    media_service = MediaService()

    notch_window    = NotchWindow(config, media_service, lyrics_engine)
    settings_dialog = SettingsDialog(config)

    # Settings opened via right-click on notch or tray menu
    settings_dialog.settings_saved.connect(notch_window.apply_geometry_from_config)
    notch_window.open_settings_requested.connect(settings_dialog.show)

    tray_manager = TrayManager(notch_window, settings_dialog, media_service)

    notch_window.show()

    # Start WinSDK media session listener in background thread
    QTimer.singleShot(200, media_service.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
