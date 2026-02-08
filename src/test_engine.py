"""
Test script for the Downloader engine.

This script tests the Downloader class by downloading a short YouTube video
to verify FFmpeg integration works correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtCore import QCoreApplication

from downloader import DownloadConfig, Downloader, MediaFormat


def on_progress(percentage: float, status: str) -> None:
    """Handle progress updates."""
    print(f"  Progress: {percentage:.1f}% - {status}")


def on_finished(filepath: Path) -> None:
    """Handle download completion."""
    print(f"\n✓ Download complete: {filepath}")
    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"  File size: {size_mb:.2f} MB")
    else:
        print("  Warning: Output file not found at expected path")
    QCoreApplication.quit()


def on_error(error_msg: str) -> None:
    """Handle errors."""
    print(f"\n✗ Error: {error_msg}")
    QCoreApplication.quit()


def main() -> int:
    """Run the download test."""
    # Create a minimal Qt application for signal/slot support
    app = QCoreApplication(sys.argv)
    
    # A very short public domain video for testing (~10 seconds)
    # "Big Buck Bunny" trailer - reliable test video
    test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"  # Big Buck Bunny (short)
    
    print("=" * 60)
    print("YoutubeBatchDownloader - Engine Test")
    print("=" * 60)
    
    # Create configuration for MP4 download
    config = DownloadConfig(
        format=MediaFormat.MP4,
        quality="best",
        web_optimize=True,
    )
    
    try:
        # Initialize downloader
        downloader = Downloader(config)
        print(f"\n✓ FFmpeg found at: {downloader.ffmpeg_path}")
        
        # Connect signals
        downloader.progress.connect(on_progress)
        downloader.finished.connect(on_finished)
        downloader.error.connect(on_error)
        
        print(f"\nStarting download: {test_url}")
        print("-" * 60)
        
        # Start download (blocking for this test)
        result = downloader.download(test_url)
        
        if result:
            print(f"\nResult path: {result}")
            return 0
        else:
            print("\nDownload returned None")
            return 1
            
    except FileNotFoundError as e:
        print(f"\n✗ FFmpeg not found: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
