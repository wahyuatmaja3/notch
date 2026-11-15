from PyQt6.QtCore import QObject, pyqtSignal

try:
    from pycaw.pycaw import AudioUtilities
    HAS_PYCAW = True
except Exception:
    HAS_PYCAW = False

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    HAS_PSUTIL = False


class SystemService(QObject):
    volume_changed = pyqtSignal(int)
    battery_changed = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self._last_vol = 50
        self._dev = None

    def _get_device(self):
        if not HAS_PYCAW:
            return None
        try:
            return AudioUtilities.GetSpeakers()
        except Exception:
            return None

    def get_volume(self) -> int:
        dev = self._get_device()
        if dev:
            try:
                if hasattr(dev, "volume_percent") and dev.volume_percent is not None:
                    return int(round(dev.volume_percent))
                elif hasattr(dev, "EndpointVolume") and dev.EndpointVolume:
                    return int(round(dev.EndpointVolume.GetMasterVolumeLevelScalar() * 100))
            except Exception as e:
                print(f"[SystemService] Error getting volume: {e}")
        return self._last_vol

    def set_volume(self, val_0_100: int):
        val = max(0, min(100, int(val_0_100)))
        self._last_vol = val
        dev = self._get_device()
        if dev:
            try:
                if hasattr(dev, "EndpointVolume") and dev.EndpointVolume:
                    dev.EndpointVolume.SetMasterVolumeLevelScalar(val / 100.0, None)
            except Exception as e:
                print(f"[SystemService] Error setting volume: {e}")
        self.volume_changed.emit(val)

    def get_battery_info(self) -> dict:
        if not HAS_PSUTIL:
            return {"percent": 100, "is_charging": True, "has_battery": False}
        try:
            b = psutil.sensors_battery()
            if b:
                return {
                    "percent": int(b.percent),
                    "is_charging": bool(b.power_plugged),
                    "has_battery": True
                }
        except Exception:
            pass
        return {"percent": 100, "is_charging": True, "has_battery": False}
