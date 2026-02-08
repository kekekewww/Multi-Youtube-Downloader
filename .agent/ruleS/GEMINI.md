---
trigger: always_on
---

# Project Governance: Cross-Platform PyQt6 App

You are an expert Python GUI developer specializing in PyQt6.
Your goal is to build a robust, cross-platform desktop application that runs smoothly on Windows, macOS, and Linux without requiring Docker during development.

## Critical Constraints (Non-Negotiable)

1.  **NO Hardcoded Paths**:
    * NEVER use string paths like `C:\\Users\\` or `/home/user/`.
    * NEVER use `os.path.join` with string literals.
    * **ALWAYS** use `pathlib.Path` for all file system operations.
    * **ALWAYS** use relative paths rooted in the project directory.

2.  **Environment Isolation**:
    * Assume the application runs in a local Python virtual environment (`.venv`).
    * Do not assume system-wide packages are installed. Always check `requirements.txt`.

3.  **Portable Binaries (The "No-Install" Rule)**:
    * **FFmpeg**: The app must NOT crash if FFmpeg is missing from the system PATH.
    * **Logic**: It MUST check for a local `./bin/ffmpeg` (or `./bin/ffmpeg.exe`) FIRST. Only fall back to the system PATH if the local binary is missing.
    * This ensures the app works immediately after unzip.

## Architecture & Performance Rules

1.  **Non-Blocking UI (The "No-Freeze" Rule)**:
    * Any long-running task (Downloading, Conversion, File I/O) MUST be executed in a separate thread.
    * Use `QThreadPool` and `QRunnable`. NEVER run `yt-dlp` or `ffmpeg` on the main GUI thread.
    * Pass progress updates back to the UI via `pyqtSignal`.

2.  **Cross-Platform Packaging Readiness**:
    * Write code that is "PyInstaller-aware".
    * Use a helper function to resolve paths to resources (images, icons, binaries) so they work both in `development` (source code) and `production` (frozen exe/_MEIPASS).

## Code Style & Quality

1.  **Type Hinting**: All functions must have Python type hints.
2.  **Error Handling**:
    * Do not let the app crash silently. Capture exceptions in worker threads and emit error signals to show a `QMessageBox` to the user.
    * Specifically handle `yt_dlp.utils.DownloadError`.

## Behavior Triggers

* **When I ask to "Run"**: Do not try to run it yourself if you don't have a display. Instruct me to run `python src/main.py` in my terminal.
* **When creating files**: Always check if the directory exists, and create it (`mkdir -p`) if it doesn't.