"""Shared pytest fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


@pytest.fixture
def temp_work_dir():
    """Create a temporary working directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_image():
    """Create a simple test image (10x10 pixels with a pattern)."""
    img = Image.new("RGB", (10, 10), color=(128, 128, 128))
    pixels = img.load()
    # Create a simple pattern: top half darker, bottom half lighter
    for y in range(5):
        for x in range(10):
            pixels[x, y] = (64, 64, 64)  # Dark
    for y in range(5, 10):
        for x in range(10):
            pixels[x, y] = (192, 192, 192)  # Light
    return img


@pytest.fixture
def sample_image_path(temp_work_dir, sample_image):
    """Save sample image to a temporary file."""
    img_path = temp_work_dir / "frame_000001.png"  # Use expected frame naming format
    sample_image.save(img_path)
    return img_path


@pytest.fixture
def mock_ffmpeg():
    """Mock ffmpeg subprocess calls."""
    with patch("video2ascii.converter.subprocess.run") as mock_run:
        # Mock successful ffmpeg execution
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture
def mock_ffprobe():
    """Mock ffprobe subprocess calls."""
    with patch("video2ascii.mp4_exporter.subprocess.run") as mock_run:
        # Mock successful ffprobe execution
        mock_result = MagicMock()
        mock_result.stdout = "1600x972"
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_font_paths(monkeypatch):
    """Mock font path existence checks."""
    def mock_exists(self):
        # Return False for all font paths (no fonts installed in test env)
        return False
    
    # Patch Path.exists for font searches
    original_exists = Path.exists
    monkeypatch.setattr(Path, "exists", mock_exists)
    
    yield


@pytest.fixture
def sample_ascii_frame():
    """Create a sample ASCII frame string."""
    return "  .:-=+*#%@\n" * 5


@pytest.fixture
def sample_ascii_frame_color():
    """Create a sample ASCII frame string with ANSI color codes."""
    return "\033[38;2;100;150;200m#\033[0m\033[38;2;200;100;50m@\033[0m\n" * 5
