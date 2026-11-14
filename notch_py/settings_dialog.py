from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame
)
from qfluentwidgets import (
    CardWidget, Slider, SwitchButton, ComboBox, PrimaryPushButton, PushButton, SubtitleLabel, CaptionLabel, setTheme, Theme
)

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Notch Settings")
        self.resize(540, 580)
        self.setStyleSheet("background-color: #181820; color: #EEEEEE;")

        setTheme(Theme.DARK)

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 16)
        main_layout.setSpacing(14)

        # Title
        title_lbl = SubtitleLabel("Notch Settings", self)
        title_lbl.setStyleSheet("color: #FFF; font-size: 18px; font-weight: bold;")
        desc_lbl = CaptionLabel("Customize your Liquid Glass Dynamic Island overlay", self)
        desc_lbl.setStyleSheet("color: #88889A; font-size: 11px;")
        main_layout.addWidget(title_lbl)
        main_layout.addWidget(desc_lbl)

        # Scroll Area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        scroll_content = QWidget()
        self.form_layout = QVBoxLayout(scroll_content)
        self.form_layout.setContentsMargins(0, 4, 10, 4)
        self.form_layout.setSpacing(10)

        # 1. Opacity Card
        self.opacity_card = CardWidget(self)
        op_layout = QHBoxLayout(self.opacity_card)
        op_text = QVBoxLayout()
        op_title = QLabel("Glass Opacity", self)
        op_title.setStyleSheet("font-weight: 600; color: #FFF;")
        op_desc = QLabel("Background transparency level", self)
        op_desc.setStyleSheet("color: #888; font-size: 10px;")
        op_text.addWidget(op_title)
        op_text.addWidget(op_desc)
        op_layout.addLayout(op_text, 1)

        self.opacity_slider = Slider(Qt.Orientation.Horizontal, self)
        self.opacity_slider.setRange(60, 100)
        self.opacity_slider.setFixedWidth(130)
        self.opacity_lbl = QLabel("92%", self)
        self.opacity_lbl.setFixedWidth(36)
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_lbl.setText(f"{v}%"))
        op_layout.addWidget(self.opacity_slider)
        op_layout.addWidget(self.opacity_lbl)
        self.form_layout.addWidget(self.opacity_card)

        # 2. Corner Radius Card
        self.radius_card = CardWidget(self)
        rad_layout = QHBoxLayout(self.radius_card)
        rad_text = QVBoxLayout()
        rad_title = QLabel("Corner Curvature", self)
        rad_title.setStyleSheet("font-weight: 600; color: #FFF;")
        rad_desc = QLabel("Pill curvature (pixels)", self)
        rad_desc.setStyleSheet("color: #888; font-size: 10px;")
        rad_text.addWidget(rad_title)
        rad_text.addWidget(rad_desc)
        rad_layout.addLayout(rad_text, 1)

        self.radius_slider = Slider(Qt.Orientation.Horizontal, self)
        self.radius_slider.setRange(16, 32)
        self.radius_slider.setFixedWidth(130)
        self.radius_lbl = QLabel("24px", self)
        self.radius_lbl.setFixedWidth(36)
        self.radius_slider.valueChanged.connect(lambda v: self.radius_lbl.setText(f"{v}px"))
        rad_layout.addWidget(self.radius_slider)
        rad_layout.addWidget(self.radius_lbl)
        self.form_layout.addWidget(self.radius_card)

        # 3. Dynamic Accent Switch Card
        self.accent_card = CardWidget(self)
        acc_layout = QHBoxLayout(self.accent_card)
        acc_text = QVBoxLayout()
        acc_title = QLabel("Dynamic Glass Accent", self)
        acc_title.setStyleSheet("font-weight: 600; color: #FFF;")
        acc_desc = QLabel("Extract vibrant glow color automatically from album art", self)
        acc_desc.setStyleSheet("color: #888; font-size: 10px;")
        acc_text.addWidget(acc_title)
        acc_text.addWidget(acc_desc)
        acc_layout.addLayout(acc_text, 1)

        self.accent_switch = SwitchButton(self)
        acc_layout.addWidget(self.accent_switch)
        self.form_layout.addWidget(self.accent_card)

        # 4. Alignment Card
        self.align_card = CardWidget(self)
        al_layout = QHBoxLayout(self.align_card)
        al_text = QVBoxLayout()
        al_title = QLabel("Screen Alignment", self)
        al_title.setStyleSheet("font-weight: 600; color: #FFF;")
        al_desc = QLabel("Horizontal alignment on monitor", self)
        al_desc.setStyleSheet("color: #888; font-size: 10px;")
        al_text.addWidget(al_title)
        al_text.addWidget(al_desc)
        al_layout.addLayout(al_text, 1)

        self.align_combo = ComboBox(self)
        self.align_combo.addItems(["Center", "Left", "Right"])
        self.align_combo.setFixedWidth(120)
        al_layout.addWidget(self.align_combo)
        self.form_layout.addWidget(self.align_card)

        # 5. Top Offset Card
        self.offset_card = CardWidget(self)
        off_layout = QHBoxLayout(self.offset_card)
        off_text = QVBoxLayout()
        off_title = QLabel("Top Distance Offset", self)
        off_title.setStyleSheet("font-weight: 600; color: #FFF;")
        off_desc = QLabel("Distance from top edge of screen", self)
        off_desc.setStyleSheet("color: #888; font-size: 10px;")
        off_text.addWidget(off_title)
        off_text.addWidget(off_desc)
        off_layout.addLayout(off_text, 1)

        self.offset_slider = Slider(Qt.Orientation.Horizontal, self)
        self.offset_slider.setRange(0, 60)
        self.offset_slider.setFixedWidth(130)
        self.offset_lbl = QLabel("12px", self)
        self.offset_lbl.setFixedWidth(36)
        self.offset_slider.valueChanged.connect(lambda v: self.offset_lbl.setText(f"{v}px"))
        off_layout.addWidget(self.offset_slider)
        off_layout.addWidget(self.offset_lbl)
        self.form_layout.addWidget(self.offset_card)

        # 6. Auto Expand Switch
        self.auto_exp_card = CardWidget(self)
        ae_layout = QHBoxLayout(self.auto_exp_card)
        ae_text = QVBoxLayout()
        ae_title = QLabel("Auto-Expand on New Track", self)
        ae_title.setStyleSheet("font-weight: 600; color: #FFF;")
        ae_desc = QLabel("Briefly expand dynamic island when song changes", self)
        ae_desc.setStyleSheet("color: #888; font-size: 10px;")
        ae_text.addWidget(ae_title)
        ae_text.addWidget(ae_desc)
        ae_layout.addLayout(ae_text, 1)

        self.auto_exp_switch = SwitchButton(self)
        ae_layout.addWidget(self.auto_exp_switch)
        self.form_layout.addWidget(self.auto_exp_card)

        # 7. Collapse Delay Card
        self.delay_card = CardWidget(self)
        del_layout = QHBoxLayout(self.delay_card)
        del_text = QVBoxLayout()
        del_title = QLabel("Collapse Inactivity Delay", self)
        del_title.setStyleSheet("font-weight: 600; color: #FFF;")
        del_desc = QLabel("Seconds before island collapses after mouse leaves", self)
        del_desc.setStyleSheet("color: #888; font-size: 10px;")
        del_text.addWidget(del_title)
        del_text.addWidget(del_desc)
        del_layout.addLayout(del_text, 1)

        self.delay_slider = Slider(Qt.Orientation.Horizontal, self)
        self.delay_slider.setRange(2, 10)
        self.delay_slider.setFixedWidth(130)
        self.delay_lbl = QLabel("5s", self)
        self.delay_lbl.setFixedWidth(36)
        self.delay_slider.valueChanged.connect(lambda v: self.delay_lbl.setText(f"{v}s"))
        del_layout.addWidget(self.delay_slider)
        del_layout.addWidget(self.delay_lbl)
        self.form_layout.addWidget(self.delay_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, 1)

        # Footer Buttons
        btn_row = QHBoxLayout()
        self.save_btn = PrimaryPushButton("Save & Apply", self)
        self.save_btn.clicked.connect(self._save_values)
        self.close_btn = PushButton("Close", self)
        self.close_btn.clicked.connect(self.hide)

        btn_row.addStretch()
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        main_layout.addLayout(btn_row)

    def _load_values(self):
        op = int(self.config.get("opacity", 0.92) * 100)
        self.opacity_slider.setValue(op)
        self.opacity_lbl.setText(f"{op}%")

        rad = int(self.config.get("corner_radius", 24))
        self.radius_slider.setValue(rad)
        self.radius_lbl.setText(f"{rad}px")

        self.accent_switch.setChecked(self.config.get("auto_accent", True))

        align = self.config.get("horizontal_alignment", "Center")
        self.align_combo.setCurrentText(align)

        top_off = int(self.config.get("vertical_offset", 12))
        self.offset_slider.setValue(top_off)
        self.offset_lbl.setText(f"{top_off}px")

        self.auto_exp_switch.setChecked(self.config.get("auto_expand_on_new_song", True))

        delay = int(self.config.get("collapse_delay", 5.0))
        self.delay_slider.setValue(delay)
        self.delay_lbl.setText(f"{delay}s")

    def _save_values(self):
        self.config.set("opacity", self.opacity_slider.value() / 100.0)
        self.config.set("corner_radius", self.radius_slider.value())
        self.config.set("auto_accent", self.accent_switch.isChecked())
        self.config.set("horizontal_alignment", self.align_combo.currentText())
        self.config.set("vertical_offset", self.offset_slider.value())
        self.config.set("auto_expand_on_new_song", self.auto_exp_switch.isChecked())
        self.config.set("collapse_delay", float(self.delay_slider.value()))

        self.settings_saved.emit()
        self.hide()
