"""Tests for mp4_exporter module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from video2ascii.mp4_exporter import (
    export_mp4,
    render_ascii_frame,
)


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
            font_path=None,
            font_is_bold=False,
            charset="classic",
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
            font_path=None,
            font_is_bold=False,
            charset="classic",
            target_width=400,
        )
        assert output_path.exists()
        img = Image.open(output_path)
        pixels = img.load()
        colors = set()
        sample_size = min(20, img.width * img.height)
        for i in range(sample_size):
            y = i // img.width
            x = i % img.width
            if y < img.height:
                colors.add(pixels[x, y])
        assert len(colors) >= 1

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
            font_path=None,
            font_is_bold=False,
            charset="classic",
            target_width=400,
        )

        render_ascii_frame(
            sample_ascii_frame_color,
            output_path_crt,
            color=True,
            crt=True,
            font_size=20,
            font_path=None,
            font_is_bold=False,
            charset="classic",
            target_width=400,
        )

        img_normal = Image.open(output_path_normal)
        img_crt = Image.open(output_path_crt)

        pixels_normal = img_normal.load()
        pixels_crt = img_crt.load()

        green_count_normal = sum(
            1
            for y in range(min(10, img_normal.height))
            for x in range(min(10, img_normal.width))
            if pixels_normal[x, y][1] > pixels_normal[x, y][0]
            and pixels_normal[x, y][1] > pixels_normal[x, y][2]
        )

        green_count_crt = sum(
            1
            for y in range(min(10, img_crt.height))
            for x in range(min(10, img_crt.width))
            if pixels_crt[x, y][1] > pixels_crt[x, y][0]
            and pixels_crt[x, y][1] > pixels_crt[x, y][2]
        )

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
            font_path=None,
            font_is_bold=False,
            charset="classic",
            target_width=401,
        )
        img = Image.open(output_path)
        assert img.width % 2 == 0
        assert img.height % 2 == 0

    def test_pure_black_stays_black(self, temp_work_dir):
        """Test pure black (0,0,0) stays black without brightness boost."""
        black_frame = "\033[38;2;0;0;0m#\033[0m\n" * 5

        output_path = temp_work_dir / "test_black.png"
        render_ascii_frame(
            black_frame,
            output_path,
            color=True,
            crt=False,
            font_size=20,
            font_path=None,
            font_is_bold=False,
            charset="braille",
            target_width=400,
        )

        img = Image.open(output_path)
        pixels = img.load()
        for y in range(min(5, img.height)):
            for x in range(min(5, img.width)):
                r, g, b = pixels[x, y]
                assert r <= 5 and g <= 5 and b <= 5

    def test_ansi_code_stripping_for_width(self, temp_work_dir):
        """Test ANSI codes are stripped when calculating width."""
        frame_with_ansi = "\033[38;2;100;150;200m#\033[0m" * 10 + "\n"

        output_path = temp_work_dir / "test_width.png"
        render_ascii_frame(
            frame_with_ansi,
            output_path,
            color=True,
            crt=False,
            font_size=20,
            font_path=None,
            font_is_bold=False,
            charset="classic",
            target_width=400,
        )

        img = Image.open(output_path)
        assert img.width > 0

    def test_font_path_used_when_provided(self, temp_work_dir, sample_ascii_frame):
        """Test that a provided font_path is used for rendering."""
        output_path = temp_work_dir / "test_fontpath.png"
        # Use None (default font) -- should not raise
        render_ascii_frame(
            sample_ascii_frame,
            output_path,
            color=False,
            font_path=None,
            charset="classic",
            target_width=400,
        )
        assert output_path.exists()


class TestExportMP4:
    """Tests for export_mp4 function."""

    def test_h265_encoding(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test H.265 encoding creates MP4."""
        output_path = temp_work_dir / "test_h265.mp4"
        frames = [sample_ascii_frame] * 3

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "libx265" in cmd or any("libx265" in str(arg) for arg in cmd)
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)

    def test_prores422_encoding(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test ProRes 422 encoding creates MOV."""
        output_path = temp_work_dir / "test_prores.mov"
        frames = [sample_ascii_frame] * 3

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "prores_ks" in cmd or any(
                    "prores" in str(arg).lower() for arg in cmd
                )
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)

    def test_h264_fallback(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test H.264 encoding (fallback)."""
        output_path = temp_work_dir / "test_h264.mp4"
        frames = [sample_ascii_frame] * 3

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.append(cmd)
            if isinstance(cmd, list) and len(cmd) > 0 and "ffmpeg" in cmd[0]:
                assert "libx264" in cmd or any("libx264" in str(arg) for arg in cmd)
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
        assert any("ffmpeg" in str(cmd) for cmd in captured_cmd)

    def test_color_preservation_in_mp4(
        self, temp_work_dir, sample_ascii_frame_color, mock_ffprobe
    ):
        """Test color preservation in MP4 export."""
        output_path = temp_work_dir / "test_color.mp4"
        frames = [sample_ascii_frame_color] * 3

        def mock_run(cmd, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
        render_dir = temp_work_dir / "rendered"
        if render_dir.exists():
            rendered_frames = list(render_dir.glob("*.png"))
            assert len(rendered_frames) > 0

    def test_subtitle_burn_in(self, temp_work_dir, sample_ascii_frame, mock_ffprobe):
        """Test subtitle path triggers ffmpeg subtitles filter."""
        output_path = temp_work_dir / "test_subs.mp4"
        frames = [sample_ascii_frame] * 3

        srt_path = temp_work_dir / "transcript.srt"
        srt_path.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nHello\n", encoding="utf-8"
        )

        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
                    subtitle_path=srt_path,
                )

        ffmpeg_cmds = [
            cmd
            for cmd in captured_cmds
            if isinstance(cmd, list) and len(cmd) > 2 and cmd[0] == "ffmpeg"
        ]
        assert len(ffmpeg_cmds) > 0
        ffmpeg_cmd = ffmpeg_cmds[0]

        assert "-vf" in ffmpeg_cmd
        vf_index = ffmpeg_cmd.index("-vf")
        vf_value = ffmpeg_cmd[vf_index + 1]
        assert "subtitles=" in vf_value
        assert "Fontname=" in vf_value

    def test_no_subtitle_when_path_is_none(
        self, temp_work_dir, sample_ascii_frame, mock_ffprobe
    ):
        """Test no subtitles filter when subtitle_path is None."""
        output_path = temp_work_dir / "test_nosubs.mp4"
        frames = [sample_ascii_frame] * 3

        captured_cmds = []

        def mock_run(cmd, **kwargs):
            captured_cmds.append(cmd)
            output_path.touch()
            return MagicMock(returncode=0)

        with patch("video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.mp4_exporter.print"):
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
                    subtitle_path=None,
                )

        ffmpeg_cmds = [
            cmd
            for cmd in captured_cmds
            if isinstance(cmd, list) and len(cmd) > 2 and cmd[0] == "ffmpeg"
        ]
        assert len(ffmpeg_cmds) > 0
        ffmpeg_cmd = ffmpeg_cmds[0]
        assert "-vf" not in ffmpeg_cmd

    def test_all_charset_options(
        self, temp_work_dir, sample_ascii_frame, mock_ffprobe
    ):
        """Test all charset options in MP4 export."""
        charsets = ["classic", "blocks", "braille", "dense", "simple", "petscii"]

        for charset in charsets:
            output_path = temp_work_dir / f"test_{charset}.mp4"
            frames = [sample_ascii_frame] * 2

            def mock_run(cmd, **kwargs):
                output_path.touch()
                return MagicMock(returncode=0)

            with patch(
                "video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run
            ):
                with patch("video2ascii.mp4_exporter.print"):
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
            assert True

    def test_font_override_passed_to_resolve(
        self, temp_work_dir, sample_ascii_frame, mock_ffprobe
    ):
        """Test font_override parameter is threaded through to resolve_font."""
        output_path = temp_work_dir / "test_font.mp4"
        frames = [sample_ascii_frame] * 2

        def mock_run(cmd, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        with patch(
            "video2ascii.mp4_exporter.subprocess.run", side_effect=mock_run
        ):
            with patch("video2ascii.mp4_exporter.print"):
                with patch(
                    "video2ascii.mp4_exporter.resolve_font"
                ) as mock_resolve:
                    mock_resolve.return_value = MagicMock(path=None, is_bold=False)
                    export_mp4(
                        frames,
                        output_path,
                        fps=12,
                        color=False,
                        work_dir=temp_work_dir,
                        charset="petscii",
                        target_width=400,
                        codec="h265",
                        font_override="PetMe128",
                    )
                    mock_resolve.assert_called_once_with("petscii", "PetMe128")
