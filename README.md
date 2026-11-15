# 🏝️ Notch v2.0 — Dynamic Island for Windows with Liquid Glass & Live Lyrics

[![Release](https://img.shields.io/github/v/release/wahyuatmaja3/notch?color=1ED760&style=flat-square)](https://github.com/wahyuatmaja3/notch/releases)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6%20%2B%20Fluent-41CD52?style=flat-square)](https://riverbankcomputing.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**Notch v2.0** adalah implementasi **Dynamic Island serbaguna untuk Windows 10 & 11** dengan estetika **Liquid Glass** transparan, terinspirasi oleh iOS Dynamic Island dan [Grump](https://yeazka.github.io/Grump/).

Notch bukan sekadar pemutar musik — ia adalah **hub produktivitas desktop** yang menyatukan musik, timer fokus, to-do list, pelacak hidrasi, kontrol volume sistem, dan notifikasi WhatsApp/Windows secara mulus di atas layar Anda.

---

## ✨ Fitur Utama v2.0

### 1. 💎 True Liquid Glass & Obsidian Themes
- **Transparansi Murni 100%**: Bebas dari artefak kotak hitam berkat per-pixel alpha composition tanpa DWM blur yang merusak sudut membulat.
- **Liquid Glass**: Efek kaca frosted transparan dengan *specular curved glare*, *ambient color glow* adaptif dari cover album atau modul aktif, dan garis tepi kaca 1.2px.
- **Obsidian Theme**: Gaya hitam pekat pekat `#08090C` elegan berkinerja tinggi dengan kontras garis tepi yang tajam.
- Slider tingkat transparansi dinamis (30% - 95%).

### 2. 📌 Mode Penempatan: Floating vs Anchored
- **Floating Mode (Kapsul Melayang)**:
  - Melayang di posisi `y = 14px` di bawah bezel monitor.
  - Tepi rounded capsule penuh (*pill shape*).
  - Dapat di-drag & drop ke mana saja di layar.
- **Anchored Mode (Menempel di Bezel Atas)**:
  - Menempel rata di tepi atas layar (`y = 0`).
  - Kurva lengkung organik (*concave flares*) yang menyatu mulus ke bezel atas monitor.
- **Quick Switch**: Klik kanan pada notch ➔ pilih `📌 Switch to Floating / Anchored Mode`.

### 3. 🚀 Modul-Modul Dynamic Island

| Modul | Tampilan Collapsed | Tampilan Expanded |
|---|---|---|
| 🎵 **Media Player** | Squircle Art + Judul / Artis / Lirik + Equalizer 4-bar | Cover 52px, tombol Mic (live synced 3-line lyrics), slider scrubber `<` `>`, circular glass buttons `⏮` `▶/⏸` `⏭` |
| ⏱️ **Pomodoro Timer** | `🍅 Focus 24:59` + ring progress mini | Countdown melingkar besar `25:00 Focus Time`, badge sesi, tombol `[⏹ Reset]`, `[▶ Start / ⏸ Pause]`, `[⏭ Skip]` |
| 📋 **Tasks & Reminders** | `📋 2 tasks pending` | Daftar tugas dengan checkbox interaktif `[✓]`, teks strikethrough, popup tambah tugas `[+ Add Task]` & `[Clear Done]` (tersimpan di SQLite `%APPDATA%/Notch/tasks.db`) |
| 💧 **Hydration Tracker** | `💧 0.75 / 2.0 L` | Indikator target harian, progress bar air biru, tombol cepat `[+250 ml]`, `[+500 ml]`, `[Reset]` |
| 🎛️ **Control Center** | `🔊 50% • 🔋 85%` | Master volume slider sistem Windows (terintegrasi via `pycaw`), info baterai laptop / desktop AC, tombol `[Mute Audio]` |
| 💬 **Notification Hub** | Muncul otomatis saat ada notif masuk (misal WhatsApp): `📱 WhatsApp: Budi — "Udah sampe belum?"` dengan cahaya neon hijau selama 4 detik | Daftar riwayat notifikasi terbaru dengan nama aplikasi, pengirim, isi pesan, dan tombol `[Clear All]` |

### 4. 🕹️ Navigasi Cepat
- **Tab Strip di Header**: Saat expanded, klik tab untuk beralih instan:
  $$\text{[ 🎵 Music ]}\quad\text{[ ⏱️ Timer ]}\quad\text{[ 📋 Tasks ]}\quad\text{[ 💧 Water ]}\quad\text{[ 🎛️ Control ]}$$
- **Double Click**: Klik 2x pada notch untuk buka/tutup (*toggle expand/collapse*).
- **Right Click Context Menu**: Beralih modul, toggle Floating/Anchored, toggle tema Liquid Glass/Obsidian, buka Settings, atau Quit.
- **System Tray**: Menu kontrol cepat, volume, dan navigasi modul.

---

## 🛠️ Instalasi & Menjalankan

### Persyaratan:
- Windows 10 atau 11 (64-bit)
- Python 3.10+ (disarankan Python 3.11)

### Menjalankan dari Source:
```bash
git clone https://github.com/wahyuatmaja3/notch.git
cd notch

# Install dependensi
pip install -r requirements.txt
# atau:
pip install PyQt6 PyQt-Fluent-Widgets winsdk pycaw psutil

# Jalankan Notch
cd notch_py
python main.py
```

### Menjalankan di Background:
Cukup klik dua kali file **`Run_Notch.bat`** di folder root untuk menjalankan Notch tanpa jendela console hitam.

---

## 📂 Struktur Project

```
d:\projects\notch\
├── docs/
│   └── PRD-Notch-v2.md                       # Product Requirements Document v2.0
├── notch_py/                                 # Implementasi Python PyQt6
│   ├── main.py                               # Entry point & single-instance mutex
│   ├── notch_window.py                       # Dynamic Island window & modular rendering
│   ├── config.py                             # Settings persistence (%APPDATA%/Notch/settings.json)
│   ├── settings_dialog.py                    # Fluent Settings Dialog v2.0
│   ├── tray_manager.py                       # System Tray integration
│   ├── media_service.py                      # Windows SMTC Media listener
│   ├── lyrics_engine.py                      # LRCLIB API & SQLite lyric cache
│   ├── color_thief.py                        # Album art accent color extractor
│   ├── services/                             # Backend services v2.0
│   │   ├── __init__.py
│   │   ├── pomodoro_service.py               # Pomodoro focus/break countdown
│   │   ├── task_service.py                   # SQLite tasks CRUD
│   │   ├── hydration_service.py              # Daily water intake tracker
│   │   ├── system_service.py                 # Windows audio volume & battery
│   │   └── notification_service.py           # WinRT toast notification listener
│   ├── build_nuitka.py                       # Nuitka compiler script
│   └── build_nuitka.bat                      # One-click Nuitka standalone build
├── Run_Notch.bat                             # One-click background launcher
└── README.md
```

---

## 📜 Lisensi & Kredit

- Dilisensikan di bawah lisensi MIT.
- Inspirasi desain: [Grump](https://yeazka.github.io/Grump/) by `yeazka` & Apple iOS Dynamic Island.
