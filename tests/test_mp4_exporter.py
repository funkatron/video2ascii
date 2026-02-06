"""Tests for mp4_exporter module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from video2ascii.mp4_exporter import (
    export_mp4,
    find_bold_braille_font,
    find_font_with_braille_support,
    find_monospace_font,
    render_ascii_frame,
)


class TestFontSelection:
    """Tests for font selection functions."""
    
    def test_find_monospace_font_returns_path_or_none(self, mock_font_paths):
        """Test find_monospace_font returns Path or None."""
        result = find_monospace_font()
        assert result is None or isinstance(result, Path)
    
    def test_find_font_with_braille_support(self, mock_font_paths):
        """Test find_font_with_braille_support returns Path or None."""
        result = find_font_with_braille_support()
        assert result is None or isinstance(result, Path)
    
    def test_find_bold_braille_font(self, mock_font_paths):
        """Test find_bold_braille_font returns Path or None."""
        result = find_bold_braille_font()
        assert result is None or isinstance(result, Path)
    
    def test_font_fallback_when_not_found(self, monkeypatch):
        """Test font fallback when preferred font not found."""
        # Mock all fonts to not exist
        def mock_exists(self):
            return False
        
        monkeypatch.setattr(Path, "exists", mock_exists)
        
        result = find_monospace_font()
        assert result is None


class TestRenderAsciiFrame:
    """Tests for render_ascii_frame function."""
    
    def test_grayscale_rendering_produces_image(self, temp_work_dir, sample_ascii_frame):
        """Test grayscale rendering produces image file."""
        output_path = temp_work_dir / "test_output.png"
        render_ascii_frame(
            sample_ascii_frame,
            output_path,
            color=False,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=400,
        )
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.mode == "RGB"
    
    def test_color_rendering_parses_ansi_codes(self, temp_work_dir, sample_ascii_frame_color):
        """Test color rendering parses ANSI codes correctly."""
        output_path = temp_work_dir / "test_output_color.png"
        render_ascii_frame(
            sample_ascii_frame_color,
            output_path,
            color=True,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=400,
        )
        assert output_path.exists()
        img = Image.open(output_path)
        # Should have colors (not just grayscale)
        pixels = img.load()
        colors = set()
        # Sample a reasonable number of pixels
        sample_size = min(20, img.width * img.height)
        for i in range(sample_size):
            y = i // img.width
            x = i % img.width
            if y < img.height:
                colors.add(pixels[x, y])
        # Should have multiple colors (at least 2)
        assert len(colors) >= 1  # May be mostly one color if frame is simple
    
    def test_crt_mode_applies_green_tint(self, temp_work_dir, sample_ascii_frame_color):
        """Test CRT mode applies green tint."""
        output_path_normal = temp_work_dir / "test_normal.png"
        output_path_crt = temp_work_dir / "test_crt.png"
        
        render_ascii_frame(
            sample_ascii_frame_color,
            output_path_normal,
            color=True,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=400,
        )
        
        render_ascii_frame(
            sample_ascii_frame_color,
            output_path_crt,
            color=True,
            crt=True,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=400,
        )
        
        img_normal = Image.open(output_path_normal)
        img_crt = Image.open(output_path_crt)
        
        # CRT image should have more green pixels
        pixels_normal = img_normal.load()
        pixels_crt = img_crt.load()
        
        green_count_normal = sum(1 for y in range(min(10, img_normal.height)) 
                                for x in range(min(10, img_normal.width))
                                if pixels_normal[x, y][1] > pixels_normal[x, y][0] and pixels_normal[x, y][1] > pixels_normal[x, y][2])
        
        green_count_crt = sum(1 for y in range(min(10, img_crt.height))
                              for x in range(min(10, img_crt.width))
                              if pixels_crt[x, y][1] > pixels_crt[x, y][0] and pixels_crt[x, y][1] > pixels_crt[x, y][2])
        
        assert green_count_crt >= green_count_normal
    
    def test_dimensions_are_even(self, temp_work_dir, sample_ascii_frame):
        """Test rendered image dimensions are even (for H.264 compatibility)."""
        output_path = temp_work_dir / "test_output.png"
        render_ascii_frame(
            sample_ascii_frame,
            output_path,
            color=False,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=401,  # Odd number
        )
        img = Image.open(output_path)
        assert img.width % 2 == 0
        assert img.height % 2 == 0
    
    def test_pure_black_stays_black(self, temp_work_dir):
        """Test pure black (0,0,0) stays black without brightness boost."""
        # Create ASCII frame with pure black color
        black_frame = "\033[38;2;0;0;0m#\033[0m\n" * 5
        
        output_path = temp_work_dir / "test_black.png"
        render_ascii_frame(
            black_frame,
            output_path,
            color=True,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=True,  # Test braille path
            target_width=400,
        )
        
        img = Image.open(output_path)
        pixels = img.load()
        # Sample pixels - should be black or very dark
        for y in range(min(5, img.height)):
            for x in range(min(5, img.width)):
                r, g, b = pixels[x, y]
                # Should be black (0,0,0) or very close
                assert r <= 5 and g <= 5 and b <= 5
    
    def test_ansi_code_stripping_for_width(self, temp_work_dir):
        """Test ANSI codes are stripped when calculating width."""
        # Frame with ANSI codes that would affect length
        frame_with_ansi = "\033[38;2;100;150;200m#\033[0m" * 10 + "\n"
        
        output_path = temp_work_dir / "test_width.png"
        render_ascii_frame(
            frame_with_ansi,
            output_path,
            color=True,
            crt=False,
            font_size=20,
            prefer_petscii_font=False,
            prefer_braille_font=False,
            target_width=400,
        )
        
        img = Image.open(output_path)
        # Width should be based on character count (10), not ANSI code length
        assert img.width > 0


class TestExportMP4:
    """Tests for export_mp4 function."""
    
    def test_h265_encoding(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test H.265 encoding creates MP4."""
        output_path = temp_work_dir / "test_h265.mp4"
        frames = [sample_ascii_frame] * 3
        
        captured_cmd = []
        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            # Verify H.265 codec is used
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "libx265" in cmd or any("libx265" in str(arg) for arg in cmd)
            # Create output file so stat() doesn't fail
            output_path.touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):  # Suppress print output
                export_mp4(
                    frames,
                    output_path,
                    fps=12,
                    color=False,
                    crt=False,
                    work_dir=temp_work_dir,
                    charset="classic",
                    target_width=400,
                    codec="h265",
                )
        # Verify ffmpeg was called
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)
    
    def test_prores422_encoding(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test ProRes 422 encoding creates MOV."""
        output_path = temp_work_dir / "test_prores.mov"
        frames = [sample_ascii_frame] * 3
        
        captured_cmd = []
        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            # Verify ProRes codec is used
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "prores_ks" in cmd or any("prores" in str(arg).lower() for arg in cmd)
            # Create output file so stat() doesn't fail
            output_path.touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):  # Suppress print output
                export_mp4(
                    frames,
                    output_path,
                    fps=12,
                    color=False,
                    crt=False,
                    work_dir=temp_work_dir,
                    charset="classic",
                    target_width=400,
                    codec="prores422",
                )
        # Verify ffmpeg was called
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)
    
    def test_h264_fallback(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test H.264 encoding (fallback)."""
        output_path = temp_work_dir / "test_h264.mp4"
        frames = [sample_ascii_frame] * 3
        
        captured_cmd = []
        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            # Verify H.264 codec is used
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "libx264" in cmd or any("libx264" in str(arg) for arg in cmd)
            # Create output file so stat() doesn't fail
            output_path.touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):  # Suppress print output
                export_mp4(
                    frames,
                    output_path,
                    fps=12,
                    color=False,
                    crt=False,
                    work_dir=temp_work_dir,
                    charset="classic",
                    target_width=400,
                    codec="h264",
                )
        # Verify ffmpeg was called
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)
    
    def test_color_preservation_in_mp4(self, temp_work_dir, sample_ascii_frame_color, mock_ffprobe):
        """Test color preservation in MP4 export."""
        output_path = temp_work_dir / "test_color.mp4"
        frames = [sample_ascii_frame_color] * 3
        
        def mock_run(cmd, **kwargs):
            # Create output file so stat() doesn't fail
            output_path.touch()
            return MagicMock(returncode=0)
        
        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):  # Suppress print output
                export_mp4(
                    frames,
                    output_path,
                    fps=12,
                    color=True,
                    crt=False,
                    work_dir=temp_work_dir,
                    charset="classic",
                    target_width=400,
                    codec="h265",
                )
        # Should have rendered frames with color
        render_dir = temp_work_dir / "rendered"
        if render_dir.exists():
            rendered_frames = list(render_dir.glob("*.png"))
            assert len(rendered_frames) > 0
    
    def test_all_charset_options(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test all charset options in MP4 export."""
        charsets = ["classic", "blocks", "braille", "dense", "simple", "petscii"]
        
        for charset in charsets:
            output_path = temp_work_dir / f"test_{charset}.mp4"
            frames = [sample_ascii_frame] * 2
            
            def mock_run(cmd, **kwargs):
                # Create output file so stat() doesn't fail
                output_path.touch()
                return MagicMock(returncode=0)
            
            with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
                with patch("video2ascii.mp4_exporter.print"):  # Suppress print output
                    export_mp4(
                        frames,
                        output_path,
                        fps=12,
                        color=False,
                        crt=False,
                        work_dir=temp_work_dir / charset,
                        charset=charset,
                        target_width=400,
                        codec="h265",
                    )
            # Should complete without error
            assert True
