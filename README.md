# 🎵 Notch — Dynamic Island for Windows with Live Lyrics

**Notch** adalah aplikasi Dynamic Island untuk Windows dengan estetika modern **Liquid Glass**, yang menampilkan informasi lagu real-time dan **lirik berjalan (synced lyrics)** dari pemutar musik berbasis browser seperti **YouTube Music** dan **Spotify** (Google Chrome, Brave, Mozilla Firefox, Microsoft Edge).

Aplikasi ini tersedia dalam dua implementasi berkinerja tinggi:
1. **.NET 8 Self-Contained Standalone Executable** (`dist/Notch.exe`): Single-file `.exe` langsung jalan tanpa runtime atau instalasi.
2. **Python / PyQt6 + PyQt-Fluent-Widgets + DWM Acrylic Blur** (`notch_py/`): Tampilan ultra-modern dengan efek kaca cair (Liquid Glass), Windows DWM Acrylic Blur Behind, spring property animation 60fps, dan script compiler Nuitka standalone.

---

## ✨ Fitur Utama

- 🏝️ **MSTSC-Inspired Organic Fluid Blob**: Bentuk tab organik yang muncul menempel dari tepi atas layar (`y=0`) dengan kurva lengkung fillet samping halus (*concave flares*) seperti bar MSTSC remote desktop namun dengan sentuhan estetika modern.
- 💎 **ReactBits-Inspired Liquid Glass & Windows Acrylic**:
  - Efek kaca frosted obsidian dark transparan dengan Windows DWM Acrylic Blur Behind (`WindowEffect`).
  - Refleksi cahaya lengkung atas (*specular highlight glare*).
  - *Glowing rim border* dengan gradien tipis 1px dan ambient mood glow yang selaras dengan cover album.
  - Warna aksen dinamis (*adaptive tinting*) yang diekstrak secara otomatis dari cover album musik.
- 🔽 **Floating Collapse Handle di Bawah Notch**: Tombol minimize/collapse dipisahkan ke bawah notch berupa pil kaca mengambang independen dengan chevron minimal modern `▲`.
- 🎛️ **Kontrol Minimalis & Bebas Clutter**: Tombol settings gear dihilangkan dari tubuh notch dan dialihkan ke klik kanan context menu Fluent dan System Tray. Tombol media (Previous, Play/Pause, Next) digambar secara vektor murni (bebas glitch warna emoji) dengan efek glowing play button.
- 🎤 **Live Synced Lyrics**: Mengambil lirik bersinkronisasi waktu (format LRC) otomatis dari API LRCLIB, menampilkan 3 baris lirik (sebelumnya, aktif dengan *ambient capsule glow*, dan baris berikutnya), dengan cache lokal **SQLite** untuk akses instan.
- ⚡ **Deteksi Musik Otomatis (SMTC)**: Menggunakan **Windows Media Session API** — otomatis mendeteksi musik yang diputar di **Google Chrome, Brave, Mozilla Firefox, Microsoft Edge**, maupun aplikasi desktop Spotify tanpa konfigurasi tambahan.
- 🔌 **Browser Extension ("Notch Bridge")**: Ekstensi pendukung untuk YouTube Music & Spotify Web via WebSocket lokal (port 7891).
- ⏯️ **Media Controls**: Kontrol lagu (Play/Pause, Next Track, Previous Track) langsung dari notch atau system tray.
- 📌 **System Tray Integration**: Ikon di area notifikasi Windows dengan menu kontrol cepat, status lagu, toggle tampilkan/sembunyikan, dan akses ke menu pengaturan.
- ⚙️ **Modern Fluent Settings**: Kustomisasi tampilan (opacity, corner radius, tema), posisi (offset atas, perataan tengah/kiri/kanan, lebar), perilaku (auto-expand, delay collapse), dan kalibrasi sync offset lirik.

---

## 🛠️ Skill yang Ditambahkan ke Project

Project ini telah dibekali dengan Antigravity Workspace Skill baru:
👉 **[modern-gui-liquid-glass](file:///D:/projects/notch/.agents/skills/modern-gui-liquid-glass/SKILL.md)**

Mencakup panduan, resep kode, dan arsitektur untuk:
- **UI Framework Utama**: PyQt6, PyQt-Fluent-Widgets, PySide6, CustomTkinter, Flet, PyWebView.
- **Efek Liquid Glass / DWM Blur**: PyQt-Frameless-Window (`qframelesswindow.WindowEffect`), Acrylic blur, Mica, dan custom QPainter specular refraction.
- **Animasi Spring Qt**: `QPropertyAnimation` dengan easing curve `QEasingCurve.Type.OutCubic` / `OutBack`.
- **Compiler Standalone EXE Cepat**: Konfigurasi Nuitka standalone compiler untuk menghasilkan `.exe` native yang sangat cepat dan ringan.

---

## 📂 Struktur Rilis & Project

```
d:\projects\notch\
├── .agents/skills/modern-gui-liquid-glass/   # Workspace Skill Antigravity
│   └── SKILL.md
├── dist/
│   ├── Notch.exe                             # .NET 8 Single-File Portable (.exe)
│   └── browser-extension/                    # Ekstensi browser (Chrome, Brave, Firefox)
├── notch_py/                                 # Implementasi PyQt6 + Liquid Glass + Fluent
│   ├── main.py                               # Entry point
│   ├── notch_window.py                       # Dynamic Island Liquid Glass Window
│   ├── settings_dialog.py                    # Fluent Settings Dialog (CardWidgets, Sliders)
│   ├── tray_manager.py                       # System Tray dengan RoundMenu
│   ├── media_service.py                      # WinSDK SMTC Media Listener
│   ├── lyrics_engine.py                      # LRCLIB API & SQLite Cache
│   ├── color_thief.py                        # Dynamic Album Art Accent Extraction
│   ├── config.py                             # Settings Persistence
│   ├── build_nuitka.py                       # Nuitka Standalone Compiler Script
│   └── build_nuitka.bat                      # One-click Nuitka build
└── README.md
```

---

## 🚀 Cara Menjalankan

### Opsi 1: Menjalankan `.exe` Portable (Langsung Tanpa Install)
1. Buka folder `dist`.
2. Dobel-klik file **`Notch.exe`**.
3. Notch akan langsung muncul di atas layar dan ikon aktif di System Tray.

### Opsi 2: Menjalankan Versi Python PyQt6 (Liquid Glass Edition)
```bash
cd d:\projects\notch\notch_py
python main.py
```

### Opsi 3: Compile Versi Python ke Standalone EXE dengan Nuitka
Cukup jalankan script batch yang sudah disiapkan:
```bash
cd d:\projects\notch\notch_py
build_nuitka.bat
```
Atau jalankan:
```bash
python build_nuitka.py
```
Hasil file `.exe` super cepat akan otomatis dibuat di folder `dist_py/Notch_LiquidGlass.exe`.

---

## 🖱️ Kontrol & Interaksi

- **Hover**: Arahkan kursor ke notch untuk membuka tampilan lirik dan kontrol lengkap (*Expand*).
- **Double Click**: Klik 2x pada notch untuk toggle expand/collapse manual.
- **Drag & Drop**: Klik kiri dan tahan pada notch untuk memindahkannya ke posisi mana pun di layar.
- **Klik Kanan Tray Icon**: Membuka menu cepat (Play/Pause, Next/Previous, Settings, Exit).

---

## 🌐 Memasang Ekstensi Browser (Opsional)

Aplikasi sudah dapat mendeteksi lagu secara otomatis melalui **Windows Media Session (SMTC)**. Jika ingin menggunakan ekstensi:
- **Chrome / Brave:** Buka `chrome://extensions` ➔ Aktifkan **Developer mode** ➔ Klik **Load unpacked** ➔ Pilih folder `dist/browser-extension`.
- **Firefox:** Buka `about:debugging#/runtime/this-firefox` ➔ Klik **Load Temporary Add-on...** ➔ Pilih `manifest.json` di `dist/browser-extension`.
