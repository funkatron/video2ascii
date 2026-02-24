"""Tests for CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video2ascii.cli import main, parse_args
from video2ascii.presets import CRT_GREEN, C64_BLUE

# ---------------------------------------------------------------------------
# parse_args helpers
# ---------------------------------------------------------------------------


class TestParseArgs:
    """Tests for parse_args function."""
    
    def test_all_argument_flags(self, temp_work_dir):
        """Test all argument flags parse correctly."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video),
                                "--width", "120",
                                "--fps", "15",
                                "--color",
                                "--preset", "crt",
                                "--loop",
                                "--speed", "1.5",
                                "--invert",
                                "--edge",
                                "--edge-threshold", "0.2",
                                "--charset", "blocks",
                                "--progress",
                                "--aspect-ratio", "1.5",
                                "--verbose"]):
            args = parse_args()
        
        # Explicit --width overrides preset's width
        assert args.width == 120
        assert args.fps == 15
        assert args.color is True
        assert args.preset == "crt"
        assert args.loop is True
        assert args.speed == 1.5
        assert args.invert is True
        assert args.edge is True
        assert args.edge_threshold == 0.2
        assert args.charset == "blocks"
        assert args.progress is True
        assert args.aspect_ratio == 1.5
        assert args.verbose is True
    
    def test_default_values(self, temp_work_dir):
        """Test default values."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video)]):
            args = parse_args()
        
        assert args.width == 160
        assert args.fps == 12
        assert args.color is False
        assert args.preset is None
        assert args.speed == 1.0
        assert args.charset == "classic"
        assert args.verbose is False
        assert args.color_scheme is None
        assert args.crt_filter is False
    
    def test_width_validation(self, temp_work_dir):
        """Test width validation (must be >= 20)."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--width", "19"]):
            with pytest.raises(SystemExit):
                parse_args()
    
    def test_fps_validation(self, temp_work_dir):
        """Test fps validation (must be >= 1)."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--fps", "0"]):
            with pytest.raises(SystemExit):
                parse_args()
    
    def test_speed_validation(self, temp_work_dir):
        """Test speed validation (must be > 0)."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--speed", "0"]):
            with pytest.raises(SystemExit):
                parse_args()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--speed", "-1"]):
            with pytest.raises(SystemExit):
                parse_args()
    
    def test_crt_flag_maps_to_preset(self, temp_work_dir):
        """Test --crt is shorthand for --preset crt."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--crt"]):
            args = parse_args()
        
        assert args.preset == "crt"
        assert args.color_scheme is CRT_GREEN
        assert args.crt_filter is True
        assert args.width == 80
        assert args.color is True

    def test_preset_c64(self, temp_work_dir):
        """Test --preset c64 applies C64 settings."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--preset", "c64"]):
            args = parse_args()
        
        assert args.preset == "c64"
        assert args.color_scheme is C64_BLUE
        assert args.crt_filter is True
        assert args.width == 40
        assert args.charset == "petscii"
        assert args.color is True

    def test_preset_overridden_by_explicit_flags(self, temp_work_dir):
        """Test explicit CLI flags override preset values."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--preset", "c64", "--width", "60"]):
            args = parse_args()
        
        assert args.width == 60  # overridden
        assert args.charset == "petscii"  # from preset

    def test_crt_flag_does_not_override_explicit_preset(self, temp_work_dir):
        """Test --crt doesn't override an explicit --preset."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--preset", "c64", "--crt"]):
            args = parse_args()
        
        assert args.preset == "c64"  # explicit --preset takes priority
    
    def test_invalid_input_file(self, temp_work_dir):
        """Test invalid input file path raises error."""
        with patch("sys.argv", ["video2ascii", str(temp_work_dir / "nonexistent.mp4")]):
            with pytest.raises(SystemExit):
                parse_args()
    
    def test_verbose_enables_debug_logging(self, temp_work_dir, caplog):
        """Test verbose flag enables debug logging."""
        import logging
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--verbose"]):
            args = parse_args()
        assert args.verbose is True
        
        with caplog.at_level(logging.DEBUG):
            assert logging.getLogger().level == logging.DEBUG


class TestMain:
    """Tests for main function."""
    
    def test_export_mode(self, temp_work_dir, sample_ascii_frame):
        """Test export mode (shell script)."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_script = temp_work_dir / "output.sh"
        
        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export") as mock_export:
                        sys.argv = ["video2ascii", str(test_video), "--export", str(output_script)]
                        main()
                        mock_export.assert_called_once()

    def test_export_sh_c64_preset_does_not_default_to_crt(
        self, temp_work_dir, sample_ascii_frame,
    ):
        """Test C64 preset keeps .sh default playback non-CRT."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_script = temp_work_dir / "output.sh"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export") as mock_export:
                        sys.argv = [
                            "video2ascii", str(test_video),
                            "--preset", "c64",
                            "--export", str(output_script),
                        ]
                        main()
                        mock_export.assert_called_once()
                        assert mock_export.call_args[0][3] is False

    def test_export_sh_crt_preset_defaults_to_crt(
        self, temp_work_dir, sample_ascii_frame,
    ):
        """Test CRT preset keeps .sh default playback in CRT mode."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_script = temp_work_dir / "output.sh"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export") as mock_export:
                        sys.argv = [
                            "video2ascii", str(test_video),
                            "--preset", "crt",
                            "--export", str(output_script),
                        ]
                        main()
                        mock_export.assert_called_once()
                        assert mock_export.call_args[0][3] is True
    
    def test_export_mp4_mode(self, temp_work_dir, sample_ascii_frame):
        """Test export_mp4 mode."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mp4 = temp_work_dir / "output.mp4"
        
        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = ["video2ascii", str(test_video), "--export-mp4", str(output_mp4)]
                        main()
                        mock_export.assert_called_once()
                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs.get("codec") == "h265" or "h265" in str(mock_export.call_args)
    
    def test_export_prores422_mode(self, temp_work_dir, sample_ascii_frame):
        """Test export_prores422 mode."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mov = temp_work_dir / "output.mov"
        
        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = ["video2ascii", str(test_video), "--export-prores422", str(output_mov)]
                        main()
                        mock_export.assert_called_once()
                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs.get("codec") == "prores422" or "prores422" in str(mock_export.call_args)

    def test_export_webm_mode(self, temp_work_dir, sample_ascii_frame):
        """Test export_webm mode."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_webm = temp_work_dir / "output.webm"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = ["video2ascii", str(test_video), "--export-webm", str(output_webm)]
                        main()
                        mock_export.assert_called_once()
                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs.get("codec") == "vp9" or "vp9" in str(mock_export.call_args)
    
    def test_error_handling_missing_ffmpeg(self, temp_work_dir):
        """Test error handling for missing ffmpeg."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("video2ascii.cli.check_ffmpeg") as mock_check:
            mock_check.side_effect = SystemExit(1)
            with pytest.raises(SystemExit):
                sys.argv = ["video2ascii", str(test_video)]
                main()
    
    def test_no_cache_cleanup(self, temp_work_dir, sample_ascii_frame):
        """Test cleanup with --no-cache flag."""
        import shutil
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.play"):
                        with patch("shutil.rmtree") as mock_rmtree:
                            sys.argv = ["video2ascii", str(test_video), "--no-cache"]
                            main()
                            mock_rmtree.assert_called_once()

    def test_preset_crt_threads_color_scheme(self, temp_work_dir, sample_ascii_frame):
        """Test --preset crt passes color_scheme to player."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.play") as mock_play:
                        sys.argv = ["video2ascii", str(test_video), "--preset", "crt"]
                        main()
                        call_kwargs = mock_play.call_args[1]
                        assert call_kwargs["color_scheme"] is CRT_GREEN

    def test_preset_c64_threads_color_scheme(self, temp_work_dir, sample_ascii_frame):
        """Test --preset c64 passes C64_BLUE color_scheme to player."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.play") as mock_play:
                        sys.argv = ["video2ascii", str(test_video), "--preset", "c64"]
                        main()
                        call_kwargs = mock_play.call_args[1]
                        assert call_kwargs["color_scheme"] is C64_BLUE

    def test_export_mp4_with_preset_threads_color_scheme(self, temp_work_dir, sample_ascii_frame):
        """Test --preset crt passes color_scheme to export_mp4."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mp4 = temp_work_dir / "output.mp4"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = ["video2ascii", str(test_video), "--preset", "crt", "--export-mp4", str(output_mp4)]
                        main()
                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs["color_scheme"] is CRT_GREEN


class TestSubtitleFlag:
    """Tests for --subtitle CLI flag."""

    def test_subtitle_flag_parses(self, temp_work_dir):
        """Test --subtitle flag is parsed correctly."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("sys.argv", ["video2ascii", str(test_video), "--subtitle"]):
            args = parse_args()

        assert args.subtitle is True

    def test_subtitle_default_is_false(self, temp_work_dir):
        """Test subtitle defaults to False."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("sys.argv", ["video2ascii", str(test_video)]):
            args = parse_args()

        assert args.subtitle is False

    def test_subtitle_calls_generate_srt(self, temp_work_dir, sample_ascii_frame):
        """Test --subtitle triggers SRT generation and passes segments to player."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        fake_srt = temp_work_dir / "transcript.srt"
        fake_srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nHello\n",
            encoding="utf-8",
        )

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.play") as mock_play:
                        with patch("video2ascii.subtitle.generate_srt", return_value=fake_srt):
                            sys.argv = ["video2ascii", str(test_video), "--subtitle"]
                            main()

                            call_kwargs = mock_play.call_args[1]
                            assert "subtitle_segments" in call_kwargs
                            assert call_kwargs["subtitle_segments"] is not None
                            assert len(call_kwargs["subtitle_segments"]) == 1
                            assert call_kwargs["subtitle_segments"][0][2] == "Hello"

    def test_subtitle_mp4_passes_srt_path(self, temp_work_dir, sample_ascii_frame):
        """Test --subtitle with --export-mp4 passes SRT path to exporter."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mp4 = temp_work_dir / "output.mp4"

        fake_srt = temp_work_dir / "transcript.srt"
        fake_srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nHi\n", encoding="utf-8")

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        with patch("video2ascii.subtitle.generate_srt", return_value=fake_srt):
                            sys.argv = [
                                "video2ascii", str(test_video),
                                "--subtitle", "--export-mp4", str(output_mp4),
                            ]
                            main()

                            call_kwargs = mock_export.call_args[1]
                            assert call_kwargs["subtitle_path"] == fake_srt


class TestFontFlag:
    """Tests for --font CLI flag."""

    def test_font_flag_parses(self, temp_work_dir):
        """Test --font flag is parsed correctly."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("sys.argv", ["video2ascii", str(test_video), "--font", "PetMe128"]):
            args = parse_args()

        assert args.font == "PetMe128"

    def test_font_default_is_none(self, temp_work_dir):
        """Test font defaults to None."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()

        with patch("sys.argv", ["video2ascii", str(test_video)]):
            args = parse_args()

        assert args.font is None

    def test_font_threaded_to_export_mp4(self, temp_work_dir, sample_ascii_frame):
        """Test --font is passed as font_override to export_mp4."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mp4 = temp_work_dir / "output.mp4"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = [
                            "video2ascii", str(test_video),
                            "--export-mp4", str(output_mp4),
                            "--font", "PetMe128",
                        ]
                        main()

                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs["font_override"] == "PetMe128"

    def test_font_ignored_for_sh_export(self, temp_work_dir, sample_ascii_frame):
        """Test --font is silently ignored for .sh export."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_sh = temp_work_dir / "output.sh"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export") as mock_export:
                        sys.argv = [
                            "video2ascii", str(test_video),
                            "--export", str(output_sh),
                            "--font", "PetMe128",
                        ]
                        main()
                        mock_export.assert_called_once()

    def test_font_threaded_to_prores_export(self, temp_work_dir, sample_ascii_frame):
        """Test --font is passed to export_mp4 in ProRes mode."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        output_mov = temp_work_dir / "output.mov"

        with patch("video2ascii.cli.check_ffmpeg"):
            with patch("video2ascii.cli.extract_frames") as mock_extract:
                mock_extract.return_value = [temp_work_dir / "frame_000001.png"]
                with patch("video2ascii.cli.convert_all") as mock_convert:
                    mock_convert.return_value = [sample_ascii_frame]
                    with patch("video2ascii.cli.export_mp4") as mock_export:
                        sys.argv = [
                            "video2ascii", str(test_video),
                            "--export-prores422", str(output_mov),
                            "--font", "/path/to/font.ttf",
                        ]
                        main()

                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs["font_override"] == "/path/to/font.ttf"
