from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget, QFrame
)
from qfluentwidgets import (
    CardWidget, Slider, SwitchButton, ComboBox, PrimaryPushButton, PushButton,
    SubtitleLabel, CaptionLabel, setTheme, Theme
)

class SettingsDialog(QDialog):
    settings_saved = pyqtSignal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Notch v2.0 Settings")
        self.resize(560, 640)
        self.setStyleSheet("background-color: #14161E; color: #EEEEEE;")

        setTheme(Theme.DARK)

        self._init_ui()
        self._load_values()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 18)
        main_layout.setSpacing(14)

        # Header Title
        title_lbl = SubtitleLabel("Notch v2.0 Settings", self)
        title_lbl.setStyleSheet("color: #FFF; font-size: 19px; font-weight: bold;")
        desc_lbl = CaptionLabel("Konfigurasi Dynamic Island, Tampilan Glass, dan Modul Produktivitas", self)
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
        self.form_layout.setContentsMargins(0, 4, 12, 4)
        self.form_layout.setSpacing(10)

        # ── 1. Layout Mode Card (Anchored vs Floating) ──
        self.layout_card = CardWidget(self)
        l_layout = QHBoxLayout(self.layout_card)
        l_text = QVBoxLayout()
        l_title = QLabel("Layout Mode (Posisi)", self)
        l_title.setStyleSheet("font-weight: 600; color: #FFF;")
        l_desc = QLabel("Pilih Floating (kapsul melayang) atau Anchored (menempel di bezel atas)", self)
        l_desc.setStyleSheet("color: #888; font-size: 10px;")
        l_text.addWidget(l_title)
        l_text.addWidget(l_desc)
        l_layout.addLayout(l_text, 1)

        self.layout_combo = ComboBox(self)
        self.layout_combo.addItems(["Floating (Melayang)", "Anchored (Bezel Atas)"])
        self.layout_combo.setFixedWidth(160)
        l_layout.addWidget(self.layout_combo)
        self.form_layout.addWidget(self.layout_card)

        # ── 2. Theme Style Card (Liquid Glass vs Obsidian) ──
        self.theme_card = CardWidget(self)
        t_layout = QHBoxLayout(self.theme_card)
        t_text = QVBoxLayout()
        t_title = QLabel("Visual Theme Style", self)
        t_title.setStyleSheet("font-weight: 600; color: #FFF;")
        t_desc = QLabel("Liquid Glass (frosted blur transparan) atau Obsidian (hitam pekat)", self)
        t_desc.setStyleSheet("color: #888; font-size: 10px;")
        t_text.addWidget(t_title)
        t_text.addWidget(t_desc)
        t_layout.addLayout(t_text, 1)

        self.theme_combo = ComboBox(self)
        self.theme_combo.addItems(["Liquid Glass (Transparan)", "Obsidian (Hitam Pekat)"])
        self.theme_combo.setFixedWidth(170)
        t_layout.addWidget(self.theme_combo)
        self.form_layout.addWidget(self.theme_card)

        # ── 3. Opacity Slider Card ──
        self.opacity_card = CardWidget(self)
        op_layout = QHBoxLayout(self.opacity_card)
        op_text = QVBoxLayout()
        op_title = QLabel("Glass Transparency / Opacity", self)
        op_title.setStyleSheet("font-weight: 600; color: #FFF;")
        op_desc = QLabel("Tingkat transparansi kaca (30% - 95%)", self)
        op_desc.setStyleSheet("color: #888; font-size: 10px;")
        op_text.addWidget(op_title)
        op_text.addWidget(op_desc)
        op_layout.addLayout(op_text, 1)

        self.opacity_slider = Slider(Qt.Orientation.Horizontal, self)
        self.opacity_slider.setRange(30, 95)
        self.opacity_slider.setFixedWidth(130)
        self.opacity_lbl = QLabel("72%", self)
        self.opacity_lbl.setFixedWidth(36)
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_lbl.setText(f"{v}%"))
        op_layout.addWidget(self.opacity_slider)
        op_layout.addWidget(self.opacity_lbl)
        self.form_layout.addWidget(self.opacity_card)

        # ── 4. Active Module Default ──
        self.mod_card = CardWidget(self)
        m_layout = QHBoxLayout(self.mod_card)
        m_text = QVBoxLayout()
        m_title = QLabel("Default Active Module", self)
        m_title.setStyleSheet("font-weight: 600; color: #FFF;")
        m_desc = QLabel("Modul utama yang ditampilkan di Dynamic Island", self)
        m_desc.setStyleSheet("color: #888; font-size: 10px;")
        m_text.addWidget(m_title)
        m_text.addWidget(m_desc)
        m_layout.addLayout(m_text, 1)

        self.mod_combo = ComboBox(self)
        self.mod_combo.addItems(["Media Player", "Pomodoro Timer", "Tasks & Reminders", "Hydration Tracker", "Control Center"])
        self.mod_combo.setFixedWidth(160)
        m_layout.addWidget(self.mod_combo)
        self.form_layout.addWidget(self.mod_card)

        # ── 5. Pomodoro Focus Duration ──
        self.pomo_card = CardWidget(self)
        p_layout = QHBoxLayout(self.pomo_card)
        p_text = QVBoxLayout()
        p_title = QLabel("Pomodoro Focus Duration", self)
        p_title.setStyleSheet("font-weight: 600; color: #FFF;")
        p_desc = QLabel("Durasi sesi fokus kerja (10 - 60 menit)", self)
        p_desc.setStyleSheet("color: #888; font-size: 10px;")
        p_text.addWidget(p_title)
        p_text.addWidget(p_desc)
        p_layout.addLayout(p_text, 1)

        self.pomo_slider = Slider(Qt.Orientation.Horizontal, self)
        self.pomo_slider.setRange(10, 60)
        self.pomo_slider.setFixedWidth(130)
        self.pomo_lbl = QLabel("25m", self)
        self.pomo_lbl.setFixedWidth(36)
        self.pomo_slider.valueChanged.connect(lambda v: self.pomo_lbl.setText(f"{v}m"))
        p_layout.addWidget(self.pomo_slider)
        p_layout.addWidget(self.pomo_lbl)
        self.form_layout.addWidget(self.pomo_card)

        # ── 6. Hydration Target ──
        self.hydra_card = CardWidget(self)
        h_layout = QHBoxLayout(self.hydra_card)
        h_text = QVBoxLayout()
        h_title = QLabel("Target Minum Harian", self)
        h_title.setStyleSheet("font-weight: 600; color: #FFF;")
        h_desc = QLabel("Target konsumsi air harian (1.0 - 4.0 Liter)", self)
        h_desc.setStyleSheet("color: #888; font-size: 10px;")
        h_text.addWidget(h_title)
        h_text.addWidget(h_desc)
        h_layout.addLayout(h_text, 1)

        self.hydra_slider = Slider(Qt.Orientation.Horizontal, self)
        self.hydra_slider.setRange(10, 40)
        self.hydra_slider.setFixedWidth(130)
        self.hydra_lbl = QLabel("2.0 L", self)
        self.hydra_lbl.setFixedWidth(40)
        self.hydra_slider.valueChanged.connect(lambda v: self.hydra_lbl.setText(f"{v/10:.1f} L"))
        h_layout.addWidget(self.hydra_slider)
        h_layout.addWidget(self.hydra_lbl)
        self.form_layout.addWidget(self.hydra_card)

        # ── 7. Dynamic Accent Switch ──
        self.accent_card = CardWidget(self)
        acc_layout = QHBoxLayout(self.accent_card)
        acc_text = QVBoxLayout()
        acc_title = QLabel("Dynamic Glass Accent", self)
        acc_title.setStyleSheet("font-weight: 600; color: #FFF;")
        acc_desc = QLabel("Ekstrak warna cahaya otomatis dari cover album musik", self)
        acc_desc.setStyleSheet("color: #888; font-size: 10px;")
        acc_text.addWidget(acc_title)
        acc_text.addWidget(acc_desc)
        acc_layout.addLayout(acc_text, 1)

        self.accent_switch = SwitchButton(self)
        acc_layout.addWidget(self.accent_switch)
        self.form_layout.addWidget(self.accent_card)

        # ── 8. Screen Alignment ──
        self.align_card = CardWidget(self)
        al_layout = QHBoxLayout(self.align_card)
        al_text = QVBoxLayout()
        al_title = QLabel("Screen Alignment", self)
        al_title.setStyleSheet("font-weight: 600; color: #FFF;")
        al_desc = QLabel("Perataan posisi horizontal pada layar", self)
        al_desc.setStyleSheet("color: #888; font-size: 10px;")
        al_text.addWidget(al_title)
        al_text.addWidget(al_desc)
        al_layout.addLayout(al_text, 1)

        self.align_combo = ComboBox(self)
        self.align_combo.addItems(["Center", "Left", "Right"])
        self.align_combo.setFixedWidth(120)
        al_layout.addWidget(self.align_combo)
        self.form_layout.addWidget(self.align_card)

        # ── 9. Top Floating Distance ──
        self.offset_card = CardWidget(self)
        off_layout = QHBoxLayout(self.offset_card)
        off_text = QVBoxLayout()
        off_title = QLabel("Top Distance Offset", self)
        off_title.setStyleSheet("font-weight: 600; color: #FFF;")
        off_desc = QLabel("Jarak dari tepi atas layar (mode Floating)", self)
        off_desc.setStyleSheet("color: #888; font-size: 10px;")
        off_text.addWidget(off_title)
        off_text.addWidget(off_desc)
        off_layout.addLayout(off_text, 1)

        self.offset_slider = Slider(Qt.Orientation.Horizontal, self)
        self.offset_slider.setRange(4, 50)
        self.offset_slider.setFixedWidth(130)
        self.offset_lbl = QLabel("14px", self)
        self.offset_lbl.setFixedWidth(36)
        self.offset_slider.valueChanged.connect(lambda v: self.offset_lbl.setText(f"{v}px"))
        off_layout.addWidget(self.offset_slider)
        off_layout.addWidget(self.offset_lbl)
        self.form_layout.addWidget(self.offset_card)

        # ── 10. Auto Expand & Notification Alerts ──
        self.auto_exp_card = CardWidget(self)
        ae_layout = QHBoxLayout(self.auto_exp_card)
        ae_text = QVBoxLayout()
        ae_title = QLabel("Auto-Expand on Notification / Song", self)
        ae_title.setStyleSheet("font-weight: 600; color: #FFF;")
        ae_desc = QLabel("Otomatis buka pill saat lagu berganti atau notifikasi masuk", self)
        ae_desc.setStyleSheet("color: #888; font-size: 10px;")
        ae_text.addWidget(ae_title)
        ae_text.addWidget(ae_desc)
        ae_layout.addLayout(ae_text, 1)

        self.auto_exp_switch = SwitchButton(self)
        ae_layout.addWidget(self.auto_exp_switch)
        self.form_layout.addWidget(self.auto_exp_card)

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
        # Layout Mode
        mode = self.config.get("layout_mode", "floating")
        self.layout_combo.setCurrentText("Floating (Melayang)" if mode == "floating" else "Anchored (Bezel Atas)")

        # Theme Style
        theme = self.config.get("theme_style", "liquid_glass")
        self.theme_combo.setCurrentText("Liquid Glass (Transparan)" if theme == "liquid_glass" else "Obsidian (Hitam Pekat)")

        # Opacity
        op = int(self.config.get("opacity", 0.72) * 100)
        self.opacity_slider.setValue(op)
        self.opacity_lbl.setText(f"{op}%")

        # Active Module
        mod_map = {
            "media": "Media Player",
            "pomodoro": "Pomodoro Timer",
            "tasks": "Tasks & Reminders",
            "hydration": "Hydration Tracker",
            "control_center": "Control Center"
        }
        active_m = self.config.get("active_module", "media")
        self.mod_combo.setCurrentText(mod_map.get(active_m, "Media Player"))

        # Pomodoro
        pomo_m = int(self.config.get("pomodoro_focus_min", 25))
        self.pomo_slider.setValue(pomo_m)
        self.pomo_lbl.setText(f"{pomo_m}m")

        # Hydration
        hydra_l = float(self.config.get("hydration_target_l", 2.0))
        self.hydra_slider.setValue(int(hydra_l * 10))
        self.hydra_lbl.setText(f"{hydra_l:.1f} L")

        # Accent
        self.accent_switch.setChecked(self.config.get("auto_accent", True))

        # Alignment
        align = self.config.get("horizontal_alignment", "Center")
        self.align_combo.setCurrentText(align)

        # Top offset
        top_off = int(self.config.get("floating_offset_y", 14))
        self.offset_slider.setValue(top_off)
        self.offset_lbl.setText(f"{top_off}px")

        # Auto expand
        self.auto_exp_switch.setChecked(self.config.get("auto_expand_on_new_song", True))

    def _save_values(self):
        # Layout Mode
        layout_text = self.layout_combo.currentText()
        mode = "floating" if "Floating" in layout_text else "anchored"
        self.config.set("layout_mode", mode)

        # Theme Style
        theme_text = self.theme_combo.currentText()
        theme = "liquid_glass" if "Liquid Glass" in theme_text else "obsidian"
        self.config.set("theme_style", theme)

        # Opacity
        self.config.set("opacity", self.opacity_slider.value() / 100.0)

        # Active Module
        rev_mod_map = {
            "Media Player": "media",
            "Pomodoro Timer": "pomodoro",
            "Tasks & Reminders": "tasks",
            "Hydration Tracker": "hydration",
            "Control Center": "control_center"
        }
        self.config.set("active_module", rev_mod_map.get(self.mod_combo.currentText(), "media"))

        # Pomodoro & Hydration
        self.config.set("pomodoro_focus_min", self.pomo_slider.value())
        self.config.set("hydration_target_l", self.hydra_slider.value() / 10.0)

        # Accent & Alignment
        self.config.set("auto_accent", self.accent_switch.isChecked())
        self.config.set("horizontal_alignment", self.align_combo.currentText())
        self.config.set("floating_offset_y", self.offset_slider.value())
        self.config.set("auto_expand_on_new_song", self.auto_exp_switch.isChecked())

        self.settings_saved.emit()
        self.hide()
