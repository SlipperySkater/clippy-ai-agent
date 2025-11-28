"""
Build a standalone executable for the Clippy GUI using PyInstaller.

Usage:
    python build_gui_exe.py

Requires PyInstaller to be installed (e.g., `pip install pyinstaller`).
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).parent
    gui_entry = project_root / "gui.py"

    if not shutil.which("pyinstaller"):
        print("PyInstaller is not installed. Install it with `pip install pyinstaller`.")
        sys.exit(1)

    build_cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--collect-metadata",
        "imageio",
        "--collect-metadata",
        "imageio_ffmpeg",
        "--name",
        "ClippyGUI",
        str(gui_entry),
    ]

    print("Running:", " ".join(build_cmd))
    subprocess.check_call(build_cmd, cwd=project_root)

    artifact = project_root / "dist" / ("ClippyGUI.exe" if sys.platform.startswith("win") else "ClippyGUI")
    print(f"Build complete. Launch the GUI from: {artifact}")


if __name__ == "__main__":
    main()
