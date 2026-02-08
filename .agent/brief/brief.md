# Project: YoutubeBatchDownloader (MVP)

## Objective
Build a PyQt6 GUI application to batch download videos/audio from URLs using `yt-dlp` and a local `ffmpeg`.

## Core Logic & Constraints (The "Rules of Engagement")

### 1. Environment & Paths
- **Python**: 3.10+
- **FFmpeg Strategy (CRITICAL)**: 
  - The app MUST look for the executable in `./bin/ffmpeg` (relative to the script) FIRST.
  - Only fall back to system PATH if the local binary is missing.
  - Do NOT assume the user has FFmpeg installed globally.

### 2. GUI Layout (PyQt6)
- **Input**: A `QPlainTextEdit` for pasting multiple URLs (one per line).
- **Settings**:
  - `QComboBox` for Format: [MP4, MOV, MP3, FLAC, WAV].
  - `QCheckBox` for "Web Optimize" (adds `-movflags +faststart` to ffmpeg args).
- **Feedback**: A `QProgressBar` that updates based on yt-dlp's hook.

### 3. Backend Logic (`src/downloader.py`)
- **URL Resolution**: Before downloading, verify if the URL is a redirect (like `reurl` or `bit.ly`) using `requests` to get the final long URL.
- **Concurrency**: Use `QRunnable` and `QThreadPool` so the GUI doesn't freeze.
- **Download**: Use `yt_dlp.YoutubeDL` options to handle formatting.
- **Force Single Video**: Set `noplaylist=True` in yt-dlp options to prevent accidental playlist downloads when the URL contains a `list` parameter.

### 4. Execution Plan (Updated for UV)

1.  **[x] Project Init**: 
    * Install `uv` (if not present).
    * Run `uv init` to scaffold the project.
    * Run `uv python install 3.10` to ensure correct python version.
2.  **[x] Dependencies**:
    * Add dependencies: `uv add PyQt6 yt-dlp requests`.
    * (This automatically creates `pyproject.toml` and `.venv`).
3.  **[x] Development**:
    * Instead of `python src/main.py`, use `uv run src/main.py`.

## Phase 2: Interface Specs

### `src/downloader.py`

#### Class: `Downloader(QObject)`
A QObject-based downloader class for yt-dlp integration.

**Signals:**
- `progress(float, str)`: Emits (percentage, status_string) during download.
- `finished(Path)`: Emits the `Path` to the downloaded file on success.
- `error(str)`: Emits an error message when a failure occurs.

**Public Methods:**
- `__init__(config: DownloadConfig | None = None, parent: QObject | None = None)`: Initializes the downloader with optional configuration.
- `resolve_url(url: str) -> str`: Resolves redirected URLs (e.g., bit.ly) to their final destination.
- `download(url: str) -> Path | None`: Executes the download process for a single URL. Returns the file path on success.
- `ffmpeg_path` (Property): Returns the resolved `Path` to the FFmpeg binary.

**Data Structures:**
- `MediaFormat(Enum)`: [MP4, MOV, MP3, FLAC, WAV]
- `DownloadConfig(dataclass)`:
    - `format: MediaFormat`
    - `quality: str`
    - `web_optimize: bool`
    - `output_dir: Path | None`

## Step-by-Step Instructions for Agent
1.  **[x] Setup**: Check `requirements.txt` for `PyQt6`, `yt-dlp`, `requests`.
2.  **[x] Backend**: Create `src/downloader.py`. Implement a class that accepts a URL and config options, then runs `YoutubeDL`.
3.  **Frontend**: Create `src/main.py`. Set up the UI layout described above.
4.  **Wiring**: Connect the UI "Start" button to trigger the ThreadPool.
