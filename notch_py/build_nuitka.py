import os
import sys
import subprocess
from pathlib import Path

def build():
    root = Path(__file__).resolve().parent
    icon_path = root.parent / "Resources" / "app.ico"
    out_dir = root.parent / "dist_py"
    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--onefile",
        "--windows-disable-console",
        "--enable-plugin=pyqt6",
        "--include-package=qfluentwidgets",
        "--include-package=qframelesswindow",
        "--include-package=winsdk",
        f"--windows-icon-from-ico={icon_path}",
        f"--output-dir={out_dir}",
        "--output-filename=Notch_LiquidGlass.exe",
        "main.py"
    ]

    print("Executing Nuitka build command:")
    print(" ".join(str(c) for c in cmd))
    subprocess.run(cmd, cwd=root, check=True)

if __name__ == "__main__":
    build()
