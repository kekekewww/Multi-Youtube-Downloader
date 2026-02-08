"""
Main application module for YoutubeBatchDownloader.

This module provides the PyQt6 GUI for batch downloading videos/audio.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from downloader import DownloadConfig, Downloader, MediaFormat


def get_output_dir() -> Path:
    """Get the default output directory."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "output"  # type: ignore[attr-defined]
    return Path(__file__).parent.parent / "output"


def open_folder_in_explorer(path: Path) -> None:
    """
    Open a folder in the OS file explorer.
    
    Cross-platform implementation:
    - Windows: os.startfile
    - macOS: subprocess open
    - Linux: subprocess xdg-open
    """
    path_str = str(path.resolve())
    
    if sys.platform == "win32":
        os.startfile(path_str)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", path_str], check=False)
    else:
        subprocess.run(["xdg-open", path_str], check=False)


class WorkerSignals(QObject):
    """Signals for the download worker."""

    progress = pyqtSignal(str, float, str)  # url, percentage, status
    finished = pyqtSignal(str, Path)  # url, filepath
    error = pyqtSignal(str, str)  # url, error_message


class DownloadWorker(QRunnable):
    """A QRunnable worker for downloading a single URL in a thread pool."""

    def __init__(self, url: str, config: DownloadConfig) -> None:
        super().__init__()
        self.url = url
        self.config = config
        self.signals = WorkerSignals()
        self._downloader: Downloader | None = None

    @pyqtSlot()
    def run(self) -> None:
        """Execute the download task."""
        try:
            self._downloader = Downloader(self.config)

            # Connect internal signals to worker signals
            self._downloader.progress.connect(
                lambda pct, status: self.signals.progress.emit(self.url, pct, status)
            )
            self._downloader.finished.connect(
                lambda path: self.signals.finished.emit(self.url, path)
            )
            self._downloader.error.connect(
                lambda msg: self.signals.error.emit(self.url, msg)
            )

            # Execute download
            self._downloader.download(self.url)

        except FileNotFoundError as e:
            self.signals.error.emit(self.url, str(e))
        except Exception as e:
            self.signals.error.emit(self.url, f"Unexpected error: {e}")


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YouTube Batch Downloader")
        self.setMinimumSize(600, 500)

        self._thread_pool = QThreadPool()
        self._active_downloads = 0
        self._total_downloads = 0
        self._output_dir = get_output_dir()

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # === URL Input Section ===
        url_group = QGroupBox("URLs (one per line)")
        url_layout = QVBoxLayout(url_group)

        self._url_input = QPlainTextEdit()
        self._url_input.setPlaceholderText(
            "Paste YouTube URLs here, one per line...\n"
            "Example:\n"
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ\n"
            "https://www.youtube.com/watch?v=jNQXAC9IVRw"
        )
        self._url_input.setMinimumHeight(120)
        url_layout.addWidget(self._url_input)
        layout.addWidget(url_group)

        # === Settings Section ===
        settings_group = QGroupBox("Settings")
        settings_layout = QHBoxLayout(settings_group)

        # Format selector
        format_label = QLabel("Format:")
        self._format_combo = QComboBox()
        for fmt in MediaFormat:
            self._format_combo.addItem(fmt.value.upper(), fmt)
        settings_layout.addWidget(format_label)
        settings_layout.addWidget(self._format_combo)

        settings_layout.addSpacing(20)

        # Web optimize checkbox
        self._web_optimize_check = QCheckBox("Web Optimize (fast start)")
        self._web_optimize_check.setToolTip(
            "Adds -movflags +faststart for faster web playback"
        )
        settings_layout.addWidget(self._web_optimize_check)

        settings_layout.addStretch()
        layout.addWidget(settings_group)

        # === Progress Section ===
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        progress_layout.addWidget(self._progress_bar)

        self._status_label = QLabel("Ready")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self._status_label)

        layout.addWidget(progress_group)

        # === Log Section ===
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setMinimumHeight(100)
        log_layout.addWidget(self._log_output)

        layout.addWidget(log_group)

        # === Control Buttons ===
        button_layout = QHBoxLayout()

        self._start_button = QPushButton("Start Download")
        self._start_button.setMinimumHeight(40)
        self._start_button.clicked.connect(self._on_start_clicked)
        button_layout.addWidget(self._start_button)

        self._open_folder_button = QPushButton("Open Output Folder")
        self._open_folder_button.setMinimumHeight(40)
        self._open_folder_button.clicked.connect(self._on_open_folder_clicked)
        button_layout.addWidget(self._open_folder_button)

        self._clear_button = QPushButton("Clear")
        self._clear_button.setMinimumHeight(40)
        self._clear_button.clicked.connect(self._on_clear_clicked)
        button_layout.addWidget(self._clear_button)

        layout.addLayout(button_layout)

    def _get_urls(self) -> list[str]:
        """Parse and return valid URLs from the input field."""
        text = self._url_input.toPlainText()
        urls = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and (line.startswith("http://") or line.startswith("https://")):
                urls.append(line)
        return urls

    def _get_config(self) -> DownloadConfig:
        """Build configuration from current settings."""
        selected_format = self._format_combo.currentData()
        return DownloadConfig(
            format=selected_format,
            quality="best",
            web_optimize=self._web_optimize_check.isChecked(),
        )

    def _log(self, message: str) -> None:
        """Append a message to the log output."""
        self._log_output.append(message)

    def _update_progress(self, completed: int, total: int) -> None:
        """Update the overall progress bar."""
        if total > 0:
            percentage = int((completed / total) * 100)
            self._progress_bar.setValue(percentage)

    @pyqtSlot()
    def _on_start_clicked(self) -> None:
        """Handle the start button click."""
        urls = self._get_urls()

        if not urls:
            QMessageBox.warning(self, "No URLs", "Please enter at least one valid URL.")
            return

        # Ensure output directory exists
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Disable controls during download
        self._start_button.setEnabled(False)
        self._url_input.setEnabled(False)
        self._format_combo.setEnabled(False)
        self._web_optimize_check.setEnabled(False)

        self._total_downloads = len(urls)
        self._active_downloads = len(urls)
        self._progress_bar.setValue(0)

        config = self._get_config()
        self._log(f"Starting download of {len(urls)} URL(s)...")
        self._status_label.setText(f"Downloading 0/{self._total_downloads}...")

        # Create and start workers for each URL
        for url in urls:
            worker = DownloadWorker(url, config)
            worker.signals.progress.connect(self._on_worker_progress)
            worker.signals.finished.connect(self._on_worker_finished)
            worker.signals.error.connect(self._on_worker_error)
            self._thread_pool.start(worker)

    @pyqtSlot()
    def _on_open_folder_clicked(self) -> None:
        """Handle the open folder button click."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        open_folder_in_explorer(self._output_dir)
        self._log(f"Opened folder: {self._output_dir}")

    @pyqtSlot()
    def _on_clear_clicked(self) -> None:
        """Handle the clear button click."""
        self._url_input.clear()
        self._log_output.clear()
        self._progress_bar.setValue(0)
        self._status_label.setText("Ready")

    @pyqtSlot(str, float, str)
    def _on_worker_progress(self, url: str, percentage: float, status: str) -> None:
        """Handle progress updates from a worker."""
        # Extract video ID for display
        video_id = url.split("v=")[-1][:11] if "v=" in url else url[-11:]
        self._status_label.setText(f"[{video_id}] {percentage:.0f}% - {status}")

    @pyqtSlot(str, Path)
    def _on_worker_finished(self, url: str, filepath: Path) -> None:
        """Handle worker completion."""
        self._active_downloads -= 1
        completed = self._total_downloads - self._active_downloads

        self._log(f"✓ Completed: {filepath.name}")
        self._update_progress(completed, self._total_downloads)
        self._status_label.setText(f"Downloaded {completed}/{self._total_downloads}")

        self._check_all_completed()

    @pyqtSlot(str, str)
    def _on_worker_error(self, url: str, error_msg: str) -> None:
        """Handle worker errors."""
        self._active_downloads -= 1
        completed = self._total_downloads - self._active_downloads

        self._log(f"✗ Error [{url[:50]}...]: {error_msg}")
        self._update_progress(completed, self._total_downloads)

        self._check_all_completed()

    def _check_all_completed(self) -> None:
        """Check if all downloads are complete and re-enable controls."""
        if self._active_downloads <= 0:
            self._start_button.setEnabled(True)
            self._url_input.setEnabled(True)
            self._format_combo.setEnabled(True)
            self._web_optimize_check.setEnabled(True)
            self._status_label.setText("All downloads completed!")
            self._log("=" * 40)
            self._log("All downloads finished.")


def main() -> int:
    """Run the application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern cross-platform style

    # Check FFmpeg availability before starting
    try:
        test_downloader = Downloader()
        print(f"FFmpeg found: {test_downloader.ffmpeg_path}")
    except FileNotFoundError as e:
        QMessageBox.critical(
            None,
            "FFmpeg Not Found",
            f"FFmpeg is required but was not found.\n\n{e}\n\n"
            "Please place ffmpeg.exe in the ./bin/ directory.",
        )
        return 1

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
