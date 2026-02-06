"""Tests for converter module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from video2ascii.converter import (
    CHARSETS,
    check_ffmpeg,
    convert_all,
    convert_frame,
    detect_edges,
    extract_frames,
    image_to_ascii,
)


class TestCheckFFmpeg:
    """Tests for check_ffmpeg function."""
    
    def test_ffmpeg_available(self):
        """Test that check_ffmpeg succeeds when ffmpeg is available."""
        with patch("video2ascii.converter.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            check_ffmpeg()  # Should not raise
    
    def test_ffmpeg_not_found(self):
        """Test that check_ffmpeg exits when ffmpeg is not found."""
        with patch("video2ascii.converter.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            with pytest.raises(SystemExit):
                check_ffmpeg()
    
    def test_ffmpeg_error(self):
        """Test that check_ffmpeg exits when ffmpeg returns error."""
        with patch("video2ascii.converter.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
            with pytest.raises(SystemExit):
                check_ffmpeg()


class TestExtractFrames:
    """Tests for extract_frames function."""
    
    def test_extract_frames_success(self, temp_work_dir, mock_ffmpeg):
        """Test successful frame extraction."""
        input_path = temp_work_dir / "test_video.mp4"
        input_path.touch()
        
        # Create mock frame files
        frames_dir = temp_work_dir / "frames"
        frames_dir.mkdir()
        for i in range(1, 4):
            (frames_dir / f"frame_{i:06d}.png").touch()
        
        # Mock subprocess to create frame files
        def mock_run(cmd, **kwargs):
            # Create frame files
            frames_dir.mkdir(exist_ok=True)
            for i in range(1, 4):
                (frames_dir / f"frame_{i:06d}.png").touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.converter.subprocess.run", side_effect=mock_run):
            result = extract_frames(input_path, fps=12, width=80, work_dir=temp_work_dir, crt=False)
            assert len(result) == 3
            assert all(isinstance(p, Path) for p in result)
    
    def test_crt_mode_adds_filter(self, temp_work_dir, mock_ffmpeg):
        """Test that CRT mode adds unsharp filter."""
        input_path = temp_work_dir / "test_video.mp4"
        input_path.touch()
        
        captured_cmd = []
        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            frames_dir = temp_work_dir / "frames"
            frames_dir.mkdir(exist_ok=True)
            (frames_dir / "frame_000001.png").touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.converter.subprocess.run", side_effect=mock_run):
            extract_frames(input_path, fps=12, width=80, work_dir=temp_work_dir, crt=True)
            # Check that unsharp filter is in the command
            assert any("unsharp" in str(cmd) for cmd in captured_cmd)


class TestImageToAscii:
    """Tests for image_to_ascii function."""
    
    def test_grayscale_conversion(self, sample_image):
        """Test grayscale conversion produces expected characters."""
        result = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=1.2, charset="classic")
        assert isinstance(result, str)
        assert "\n" in result
        lines = result.split("\n")
        assert len(lines) > 0
        # Should contain characters from charset
        assert any(c in result for c in CHARSETS["classic"])
    
    def test_color_conversion_includes_ansi(self, sample_image):
        """Test color conversion includes ANSI color codes."""
        result = image_to_ascii(sample_image, width=10, color=True, invert=False, aspect_ratio=1.2, charset="classic")
        assert "\033[" in result  # ANSI escape sequence
        assert "38;2;" in result  # RGB color code
    
    def test_invert_reverses_chars(self, sample_image):
        """Test invert flag reverses character order."""
        normal = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=1.2, charset="classic")
        inverted = image_to_ascii(sample_image, width=10, color=False, invert=True, aspect_ratio=1.2, charset="classic")
        # Inverted should have different character distribution
        assert normal != inverted
    
    def test_aspect_ratio_affects_height(self, sample_image):
        """Test aspect ratio affects output height."""
        low_ar = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=1.0, charset="classic")
        high_ar = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=2.0, charset="classic")
        # Higher aspect ratio should produce more lines
        assert len(high_ar.split("\n")) > len(low_ar.split("\n"))
    
    def test_all_charsets(self, sample_image):
        """Test all predefined charset options."""
        for charset_name in CHARSETS.keys():
            result = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=1.2, charset=charset_name)
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_custom_charset(self, sample_image):
        """Test custom charset string."""
        custom_chars = " .oO0"
        result = image_to_ascii(sample_image, width=10, color=False, invert=False, aspect_ratio=1.2, charset=custom_chars)
        assert isinstance(result, str)
        # Should only contain characters from custom charset
        for char in result:
            if char not in ["\n", "\r"]:
                assert char in custom_chars or char == " "


class TestDetectEdges:
    """Tests for detect_edges function."""
    
    def test_edge_detection_produces_image(self, sample_image):
        """Test edge detection produces an image."""
        result = detect_edges(sample_image, color=False, threshold=0.15)
        assert isinstance(result, Image.Image)
        assert result.size == sample_image.size
    
    def test_threshold_affects_output(self, sample_image):
        """Test threshold parameter affects edge count."""
        low_threshold = detect_edges(sample_image, color=False, threshold=0.05)
        high_threshold = detect_edges(sample_image, color=False, threshold=0.5)
        # Different thresholds should produce different results
        assert low_threshold != high_threshold
    
    def test_color_preservation(self, sample_image):
        """Test color preservation when color=True."""
        result = detect_edges(sample_image, color=True, threshold=0.15)
        assert isinstance(result, Image.Image)
        assert result.mode == "RGB"
    
    def test_grayscale_mode(self, sample_image):
        """Test grayscale mode when color=False."""
        result = detect_edges(sample_image, color=False, threshold=0.15)
        assert isinstance(result, Image.Image)
        assert result.mode == "L"


class TestConvertFrame:
    """Tests for convert_frame function."""
    
    def test_convert_frame_returns_tuple(self, sample_image_path):
        """Test convert_frame returns (frame_number, ascii_string) tuple."""
        args = (sample_image_path, 10, False, False, False, 1.2, 0.15, "classic")
        result = convert_frame(args)
        assert isinstance(result, tuple)
        assert len(result) == 2
        frame_num, ascii_str = result
        assert isinstance(frame_num, int)
        assert isinstance(ascii_str, str)
    
    def test_convert_frame_with_edge(self, sample_image_path):
        """Test convert_frame with edge detection."""
        args = (sample_image_path, 10, False, False, True, 1.2, 0.15, "classic")
        result = convert_frame(args)
        frame_num, ascii_str = result
        assert len(ascii_str) > 0
    
    def test_convert_frame_with_color(self, sample_image_path):
        """Test convert_frame with color."""
        args = (sample_image_path, 10, True, False, False, 1.2, 0.15, "classic")
        result = convert_frame(args)
        frame_num, ascii_str = result
        assert "\033[" in ascii_str  # ANSI codes present


class TestConvertAll:
    """Tests for convert_all function."""
    
    def test_convert_all_returns_list(self, sample_image_path):
        """Test convert_all returns list of ASCII strings."""
        frame_paths = [sample_image_path]
        result = convert_all(frame_paths, width=10, color=False, invert=False, edge=False, aspect_ratio=1.2, edge_threshold=0.15, charset="classic")
        assert isinstance(result, list)
        assert len(result) == 1
        assert all(isinstance(s, str) for s in result)
    
    def test_convert_all_empty_list(self):
        """Test convert_all handles empty frame list."""
        result = convert_all([], width=10, color=False, invert=False, edge=False, aspect_ratio=1.2, edge_threshold=0.15, charset="classic")
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_convert_all_multiple_frames(self, temp_work_dir, sample_image):
        """Test convert_all processes multiple frames."""
        frame_paths = []
        for i in range(3):
            img_path = temp_work_dir / f"frame_{i:06d}.png"
            sample_image.save(img_path)
            frame_paths.append(img_path)
        
        result = convert_all(frame_paths, width=10, color=False, invert=False, edge=False, aspect_ratio=1.2, edge_threshold=0.15, charset="classic")
        assert len(result) == 3
        assert all(isinstance(s, str) for s in result)


class TestCharsets:
    """Tests for CHARSETS constant."""
    
    def test_all_charsets_exist(self):
        """Test all predefined charsets exist and are non-empty."""
        assert "classic" in CHARSETS
        assert "blocks" in CHARSETS
        assert "braille" in CHARSETS
        assert "dense" in CHARSETS
        assert "simple" in CHARSETS
        assert "petscii" in CHARSETS
        
        for charset_name, charset_str in CHARSETS.items():
            assert isinstance(charset_str, str)
            assert len(charset_str) > 0
    
    def test_charset_ordering(self, sample_image):
        """Test charset ordering (darkest to lightest)."""
        # Create a gradient image
        img = Image.new("RGB", (10, 1))
        pixels = img.load()
        for x in range(10):
            brightness = int(255 * x / 9)
            pixels[x, 0] = (brightness, brightness, brightness)
        
        result = image_to_ascii(img, width=10, color=False, invert=False, aspect_ratio=1.2, charset="classic")
        # Should progress from dark to light characters
        chars = CHARSETS["classic"]
        first_char = result[0] if result else chars[0]
        last_char = result[-2] if len(result) > 1 else chars[-1]  # -2 to skip newline
        assert chars.index(first_char) < chars.index(last_char)
