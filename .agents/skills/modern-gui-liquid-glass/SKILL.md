---
name: modern-gui-liquid-glass
description: >-
  Guide and reference for developing modern Windows desktop applications with
  Liquid Glass, Acrylic, Mica blur effects, fluent widgets, smooth spring animations,
  and compiling them into high-performance standalone executables with Nuitka.
---

# Modern GUI & Liquid Glass Architecture Skill

This skill provides design patterns, architecture rules, and code recipes for creating cutting-edge Windows desktop overlay and utility applications featuring:
1. **Modern Fluent UI Frameworks**: PyQt6, PyQt-Fluent-Widgets, CustomTkinter, Flet, PyWebView.
2. **Windows DWM Blur & Liquid Glass**: DWM Composition APIs, Acrylic, Mica, and layered glass refraction.
3. **Smooth Fluid Animations**: Qt Property Animations, spring physics, dynamic geometry transitions.
4. **Fast Standalone Native Compilation**: Nuitka compiler configuration for single-file, no-console, lag-free EXEs.

---

## 1. UI Frameworks & Components

### PyQt6-Fluent-Widgets
- Repository: [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)
- Provides Windows 11 Fluent Design controls: `CardWidget`, `Slider`, `SwitchButton`, `ComboBox`, `PrimaryPushButton`, `SubtitleLabel`, `CaptionLabel`, `RoundMenu`, `SystemTrayIcon`.
- Theme support: Dark, Light, and custom QSS / accent colors.

### PyQt-Frameless-Window & DWM Blur Behind
- Repository: [zhiyiYo/PyQt-Frameless-Window](https://github.com/zhiyiYo/PyQt-Frameless-Window)
- Key Class: `qframelesswindow.WindowEffect`
- Methods:
  - `setAcrylicEffect(hWnd, gradientColor, isEnableShadow=True)`
  - `setMicaEffect(hWnd, isDarkMode=True)`
  - `setAeroEffect(hWnd)`
  - `enableBlurBehindWindow(hWnd)`

---

## 2. Liquid Glass Rendering Recipe (QPainter)

To create a genuine **Liquid Glass** effect on Windows:
1. Enable Windows DWM Acrylic / BlurBehind using `WindowEffect`.
2. Set window flags: `Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SubWindow`.
3. Set `setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)`.
4. In `paintEvent`:
   - **Layer 1: Frosted Tint**: `QPainter.fillPath(path, QColor(18, 18, 24, 180))` tinted with album art accent color `QColor(accent.red(), accent.green(), accent.blue(), 35)`.
   - **Layer 2: Top Specular Refraction Glare**: A `QLinearGradient(0, 0, 0, 22)` from `QColor(255, 255, 255, 75)` to `QColor(255, 255, 255, 0)`.
   - **Layer 3: Glowing Rim Border**: 1px gradient stroke from `QColor(255, 255, 255, 60)` at top to `QColor(accent.red(), accent.green(), accent.blue(), 100)` at bottom.
   - **Layer 4: Drop Shadow**: Gaussian blurred outer shadow.

---

## 3. Spring Animation Recipe (Dynamic Island)

Use `QPropertyAnimation` with custom easing:
```python
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect

self.anim = QPropertyAnimation(self, b"geometry")
self.anim.setDuration(280)
# Use OutCubic or OutBack for organic bouncy expansion
self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
self.anim.setStartValue(current_rect)
self.anim.setEndValue(target_rect)
self.anim.start()
```

---

## 4. Windows Media Session (SMTC) Integration

Using `winsdk`:
```python
import winsdk.windows.media.control as wmc

async def get_media_session():
    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = manager.get_current_session()
    if session:
        props = await session.try_get_media_properties_async()
        title = props.title
        artist = props.artist
        return title, artist
```

---

## 5. Nuitka Standalone Compilation

To produce a fast, stutter-free `.exe` that launches in under 1 second without PyInstaller overhead:
```bash
python -m nuitka \
    --standalone \
    --onefile \
    --windows-disable-console \
    --enable-plugin=pyqt6 \
    --windows-icon-from-ico=Resources/app.ico \
    --output-dir=dist_nuitka \
    --output-filename=Notch.exe \
    main.py
```
