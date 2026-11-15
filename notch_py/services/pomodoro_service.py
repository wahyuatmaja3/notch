import time
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

class PomodoroService(QObject):
    tick = pyqtSignal(int, int, str)        # seconds_left, total_seconds, phase
    state_changed = pyqtSignal(str)          # "idle", "running", "paused"
    phase_completed = pyqtSignal(str)        # "focus", "break"

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.focus_min = config.get("pomodoro_focus_min", 25) if config else 25
        self.break_min = config.get("pomodoro_break_min", 5) if config else 5
        
        self.phase = "focus"                 # "focus" or "break"
        self.state = "idle"                  # "idle", "running", "paused"
        self.total_seconds = self.focus_min * 60
        self.seconds_left = self.total_seconds
        self.sessions_completed = 0
        
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    @property
    def is_running(self) -> bool:
        return self.state == "running"

    @property
    def is_active(self) -> bool:
        return self.state in ("running", "paused")

    def start(self):
        if self.state == "idle":
            self.total_seconds = (self.focus_min if self.phase == "focus" else self.break_min) * 60
            self.seconds_left = self.total_seconds
        self.state = "running"
        self._timer.start()
        self.state_changed.emit(self.state)
        self.tick.emit(self.seconds_left, self.total_seconds, self.phase)

    def pause(self):
        if self.state == "running":
            self.state = "paused"
            self._timer.stop()
            self.state_changed.emit(self.state)

    def resume(self):
        if self.state == "paused":
            self.state = "running"
            self._timer.start()
            self.state_changed.emit(self.state)

    def toggle(self):
        if self.state == "running":
            self.pause()
        else:
            self.start()

    def reset(self):
        self._timer.stop()
        self.phase = "focus"
        self.state = "idle"
        self.total_seconds = self.focus_min * 60
        self.seconds_left = self.total_seconds
        self.state_changed.emit(self.state)
        self.tick.emit(self.seconds_left, self.total_seconds, self.phase)

    def skip_phase(self):
        self._timer.stop()
        if self.phase == "focus":
            self.phase = "break"
            self.total_seconds = self.break_min * 60
        else:
            self.phase = "focus"
            self.total_seconds = self.focus_min * 60
        self.seconds_left = self.total_seconds
        self.state = "idle"
        self.state_changed.emit(self.state)
        self.tick.emit(self.seconds_left, self.total_seconds, self.phase)

    def set_durations(self, focus_min: int, break_min: int):
        self.focus_min = max(1, focus_min)
        self.break_min = max(1, break_min)
        if self.state == "idle":
            self.total_seconds = (self.focus_min if self.phase == "focus" else self.break_min) * 60
            self.seconds_left = self.total_seconds
            self.tick.emit(self.seconds_left, self.total_seconds, self.phase)

    def _on_tick(self):
        if self.seconds_left > 0:
            self.seconds_left -= 1
            self.tick.emit(self.seconds_left, self.total_seconds, self.phase)
        
        if self.seconds_left <= 0:
            self._timer.stop()
            completed_phase = self.phase
            if completed_phase == "focus":
                self.sessions_completed += 1
                self.phase = "break"
                self.total_seconds = self.break_min * 60
            else:
                self.phase = "focus"
                self.total_seconds = self.focus_min * 60
            
            self.seconds_left = self.total_seconds
            self.state = "idle"
            self.phase_completed.emit(completed_phase)
            self.state_changed.emit(self.state)
            self.tick.emit(self.seconds_left, self.total_seconds, self.phase)
