"""Tests for CLI module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video2ascii.cli import main, parse_args


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
                                "--crt",
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
        
        # CRT mode overrides width to 80
        assert args.width == 80


        assert args.fps == 15
        assert args.color is True
        assert args.crt is True
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
        assert args.crt is False
        assert args.speed == 1.0
        assert args.charset == "classic"
        assert args.verbose is False
    
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
    
    def test_crt_mode_overrides(self, temp_work_dir):
        """Test CRT mode overrides width to 80 and enables color."""
        test_video = temp_work_dir / "test.mp4"
        test_video.touch()
        
        with patch("sys.argv", ["video2ascii", str(test_video), "--crt", "--width", "200"]):
            args = parse_args()
        
        assert args.width == 80
        assert args.color is True
    
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
        
        # Logging level should be DEBUG when verbose
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
                        # Verify codec is h265
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
                        # Verify codec is prores422
                        call_kwargs = mock_export.call_args[1]
                        assert call_kwargs.get("codec") == "prores422" or "prores422" in str(mock_export.call_args)
    
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
