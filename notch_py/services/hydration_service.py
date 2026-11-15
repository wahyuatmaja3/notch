import time
from PyQt6.QtCore import QObject, pyqtSignal

class HydrationService(QObject):
    intake_updated = pyqtSignal(float, float)  # current_l, target_l

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.target_l = config.get("hydration_target_l", 2.0) if config else 2.0
        self.current_l = 0.0
        self.last_drank_time = time.time()

    def drink(self, amount_l: float = 0.25):
        self.current_l = round(self.current_l + amount_l, 2)
        self.last_drank_time = time.time()
        self.intake_updated.emit(self.current_l, self.target_l)

    def reset(self):
        self.current_l = 0.0
        self.last_drank_time = time.time()
        self.intake_updated.emit(self.current_l, self.target_l)

    def set_target(self, target_l: float):
        self.target_l = max(0.5, round(target_l, 1))
        self.intake_updated.emit(self.current_l, self.target_l)
