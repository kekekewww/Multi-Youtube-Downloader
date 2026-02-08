"""
Downloader module for YoutubeBatchDownloader.

This module provides the Downloader class for downloading videos/audio
using yt-dlp with local FFmpeg support.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import requests
import yt_dlp
from PyQt6.QtCore import QObject, pyqtSignal


class MediaFormat(Enum):
    """Supported media output formats."""
    MP4 = "mp4"
    MOV = "mov"
    MP3 = "mp3"
    FLAC = "flac"
    WAV = "wav"


@dataclass
class DownloadConfig:
    """Configuration for a download job."""
    format: MediaFormat = MediaFormat.MP4
    quality: str = "best"
    web_optimize: bool = False
    output_dir: Path | None = None


class Downloader(QObject):
    """
    A QObject-based downloader class for yt-dlp integration.
    
    Signals:
        progress: Emits (percentage: float, status: str) during download.
        finished: Emits (filepath: Path) when download completes successfully.
        error: Emits (error_message: str) when an error occurs.
    """
    
    progress = pyqtSignal(float, str)
    finished = pyqtSignal(Path)
    error = pyqtSignal(str)
    
    def __init__(self, config: DownloadConfig | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config or DownloadConfig()
        self._ffmpeg_path: Path | None = None
        self._resolve_ffmpeg()
    
    def _get_project_root(self) -> Path:
        """Get the project root directory."""
        # Handle both development and PyInstaller frozen modes
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS)  # type: ignore[attr-defined]
        return Path(__file__).parent.parent
    
    def _resolve_ffmpeg(self) -> None:
        """
        Resolve FFmpeg binary path.
        
        Priority:
        1. Local ./bin/ffmpeg.exe (or ffmpeg on Unix)
        2. System PATH
        
        Raises:
            FileNotFoundError: If FFmpeg cannot be found.
        """
        project_root = self._get_project_root()
        
        # Check local bin directory first
        if sys.platform == "win32":
            local_ffmpeg = project_root / "bin" / "ffmpeg.exe"
        else:
            local_ffmpeg = project_root / "bin" / "ffmpeg"
        
        if local_ffmpeg.exists():
            self._ffmpeg_path = local_ffmpeg
            return
        
        # Fall back to system PATH
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            self._ffmpeg_path = Path(system_ffmpeg)
            return
        
        raise FileNotFoundError(
            "FFmpeg not found. Please place ffmpeg in ./bin/ or install it system-wide."
        )
    
    @property
    def ffmpeg_path(self) -> Path:
        """Get the resolved FFmpeg path."""
        if self._ffmpeg_path is None:
            raise FileNotFoundError("FFmpeg path not resolved.")
        return self._ffmpeg_path
    
    def resolve_url(self, url: str) -> str:
        """
        Resolve redirected URLs to their final destination.
        
        Args:
            url: The URL to resolve.
            
        Returns:
            The final resolved URL.
        """
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            return response.url
        except requests.RequestException:
            # If resolution fails, return original URL
            return url
    
    def _build_ydl_options(self, output_path: Path) -> dict:
        """Build yt-dlp options based on configuration."""
        # Determine if this is an audio-only format
        is_audio = self._config.format in (MediaFormat.MP3, MediaFormat.FLAC, MediaFormat.WAV)
        
        options: dict = {
            "ffmpeg_location": str(self._ffmpeg_path),
            "outtmpl": str(output_path / "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,  # Only download single video, ignore playlist
            "progress_hooks": [self._progress_hook],
        }
        
        if is_audio:
            options["format"] = "bestaudio/best"
            options["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": self._config.format.value,
                "preferredquality": "192" if self._config.format == MediaFormat.MP3 else "0",
            }]
        else:
            # Video formats
            options["format"] = f"bestvideo[ext={self._config.format.value}]+bestaudio/best[ext={self._config.format.value}]/best"
            options["merge_output_format"] = self._config.format.value
            
            if self._config.web_optimize:
                options["postprocessor_args"] = {
                    "ffmpeg": ["-movflags", "+faststart"]
                }
        
        return options
    
    def _progress_hook(self, d: dict) -> None:
        """Progress hook for yt-dlp."""
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                percentage = (downloaded / total) * 100
                status = d.get("_percent_str", f"{percentage:.1f}%")
                self.progress.emit(percentage, status.strip())
        elif d["status"] == "finished":
            self.progress.emit(100.0, "Processing...")
    
    def download(self, url: str) -> Path | None:
        """
        Download a video/audio from the given URL.
        
        Args:
            url: The URL to download from.
            
        Returns:
            The path to the downloaded file, or None if an error occurred.
        """
        # Resolve redirects
        resolved_url = self.resolve_url(url)
        
        # Determine output directory
        output_dir = self._config.output_dir or (self._get_project_root() / "output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        options = self._build_ydl_options(output_dir)
        
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(resolved_url, download=True)
                if info:
                    # Get the output filename
                    filename = ydl.prepare_filename(info)
                    # Adjust extension for audio formats
                    if self._config.format in (MediaFormat.MP3, MediaFormat.FLAC, MediaFormat.WAV):
                        filename = Path(filename).with_suffix(f".{self._config.format.value}")
                    else:
                        filename = Path(filename)
                    
                    self.finished.emit(filename)
                    return filename
        except yt_dlp.utils.DownloadError as e:
            error_msg = f"Download failed: {e}"
            self.error.emit(error_msg)
            return None
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            self.error.emit(error_msg)
            return None
        
        return None
