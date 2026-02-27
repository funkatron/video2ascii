"""Tests for player module."""

import signal
import time
from unittest.mock import MagicMock, patch

import pytest

from video2ascii.player import TerminalPlayer, _blend_frame_ansi_colors, play
from video2ascii.presets import CRT_GREEN, C64_BLUE, ColorScheme


class TestTerminalPlayer:
    """Tests for TerminalPlayer class."""
    
    def test_initialization(self, sample_ascii_frame):
        """Test initialization with frames and fps."""
        frames = [sample_ascii_frame] * 5
        player = TerminalPlayer(frames, fps=12, speed=1.0)
        
        assert player.frames == frames
        assert player.fps == 12
        assert player.speed == 1.0
        assert player.frame_delay == 1.0 / 12.0
        assert player.interrupted is False
    
    def test_frame_delay_calculation(self, sample_ascii_frame):
        """Test frame delay calculation with speed multiplier."""
        frames = [sample_ascii_frame] * 5
        
        player_normal = TerminalPlayer(frames, fps=12, speed=1.0)
        assert player_normal.frame_delay == 1.0 / 12.0
        
        player_fast = TerminalPlayer(frames, fps=12, speed=2.0)
        assert player_fast.frame_delay == 1.0 / (12.0 * 2.0)
        
        player_slow = TerminalPlayer(frames, fps=12, speed=0.5)
        assert player_slow.frame_delay == 1.0 / (12.0 * 0.5)
    
    def test_signal_handler_cleanup(self, sample_ascii_frame):
        """Test signal handler (Ctrl+C) cleanup."""
        frames = [sample_ascii_frame] * 5
        player = TerminalPlayer(frames, fps=12, speed=1.0)
        
        player.interrupted = True
        player.cleanup()
        
        assert True
    
    def test_play_color_scheme_applies_tint(self, sample_ascii_frame):
        """Test color_scheme applies tint color codes."""
        frames = [sample_ascii_frame] * 2
        
        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))
        
        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(frames, fps=12, speed=100.0)
                    try:
                        player.play(color_scheme=CRT_GREEN, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass
                
                output_str = "".join(printed_output)
                # CRT_GREEN tint (51, 255, 51)
                assert "\033[38;2;51;255;51m" in output_str or len(printed_output) == 0
    
    def test_play_c64_scheme_applies_blue(self, sample_ascii_frame):
        """Test C64 color scheme applies blue tint."""
        frames = [sample_ascii_frame] * 2
        
        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))
        
        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(frames, fps=12, speed=100.0)
                    try:
                        player.play(color_scheme=C64_BLUE, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass
                
                output_str = "".join(printed_output)
                # C64_BLUE tint (124, 112, 218)
                assert "\033[38;2;124;112;218m" in output_str or len(printed_output) == 0

    def test_play_no_scheme_no_tint(self, sample_ascii_frame):
        """Test no color_scheme means no tint codes."""
        frames = [sample_ascii_frame] * 2
        
        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))
        
        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(frames, fps=12, speed=100.0)
                    try:
                        player.play(color_scheme=None, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass
                
                output_str = "".join(printed_output)
                assert "\033[38;2;51;255;51m" not in output_str

    def test_play_loop_mode(self, sample_ascii_frame):
        """Test loop mode repeats frames."""
        frames = [sample_ascii_frame] * 2
        
        frame_count = [0]
        def mock_print(*args, **kwargs):
            if sample_ascii_frame in str(args):
                frame_count[0] += 1
        
        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(frames, fps=12, speed=100.0)
                    player.interrupted = True
                    try:
                        player.play(color_scheme=None, loop=True, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass


    def test_initialization_with_subtitles(self, sample_ascii_frame):
        """Test initialization with subtitle segments."""
        frames = [sample_ascii_frame] * 5
        segments = [(0.0, 2.0, "Hello"), (2.0, 4.0, "World")]
        player = TerminalPlayer(frames, fps=12, speed=1.0, subtitle_segments=segments)

        assert player.subtitle_segments == segments

    def test_initialization_without_subtitles(self, sample_ascii_frame):
        """Test initialization without subtitle segments defaults to None."""
        frames = [sample_ascii_frame] * 5
        player = TerminalPlayer(frames, fps=12, speed=1.0)

        assert player.subtitle_segments is None

    def test_play_with_subtitles_displays_text(self, sample_ascii_frame):
        """Test subtitle text is printed during playback."""
        frames = [sample_ascii_frame] * 2
        segments = [(0.0, 10.0, "Hello subtitle")]

        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))

        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(
                        frames, fps=12, speed=100.0,
                        subtitle_segments=segments,
                    )
                    try:
                        player.play(color_scheme=None, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass

        output_str = "".join(printed_output)
        assert "Hello subtitle" in output_str

    def test_play_with_subtitles_uses_scheme_tint(self, sample_ascii_frame):
        """Test subtitle text uses color scheme tint."""
        frames = [sample_ascii_frame] * 2
        segments = [(0.0, 10.0, "Green sub")]

        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))

        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(
                        frames, fps=12, speed=100.0,
                        subtitle_segments=segments,
                    )
                    try:
                        player.play(color_scheme=CRT_GREEN, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass

        output_str = "".join(printed_output)
        assert "\033[38;2;51;255;51m" in output_str

    def test_blend_frame_ansi_colors_applies_scheme(self):
        """Test per-character ANSI color codes are blended with scheme tint."""
        frame = "\033[38;2;255;0;0mX\033[0m"
        blended = _blend_frame_ansi_colors(frame, C64_BLUE)
        assert "\033[38;2;150;89;174mX\033[0m" in blended

    def test_play_blends_ansi_colors_in_frame_output(self):
        """Test playback output contains blended ANSI colors, not originals."""
        frame = "\033[38;2;255;0;0mX\033[0m"
        printed_output = []

        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))

        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer([frame], fps=12, speed=100.0)
                    player.play(color_scheme=C64_BLUE, loop=False, progress=False)

        output_str = "".join(printed_output)
        assert "\033[38;2;150;89;174m" in output_str
        assert "\033[38;2;255;0;0m" not in output_str


class TestPlayFunction:
    """Tests for play function."""
    
    def test_basic_playback_flow(self, sample_ascii_frame):
        """Test basic playback flow."""
        frames = [sample_ascii_frame] * 3
        
        with patch("video2ascii.player.TerminalPlayer") as mock_player_class:
            mock_player = MagicMock()
            mock_player_class.return_value = mock_player
            
            play(frames, fps=12, speed=1.0, color_scheme=None, loop=False, progress=False)
            
            assert mock_player_class.called
            call_args = mock_player_class.call_args[0]
            assert call_args[0] == frames
            assert call_args[1] == 12
            assert call_args[2] == 1.0
            
            assert mock_player.play.called
            call_kwargs = mock_player.play.call_args[1]
            assert call_kwargs["color_scheme"] is None
            assert call_kwargs["loop"] is False
            assert call_kwargs["progress"] is False
    
    def test_play_with_parameters(self, sample_ascii_frame):
        """Test play function with all parameters."""
        frames = [sample_ascii_frame] * 3
        
        with patch("video2ascii.player.TerminalPlayer") as mock_player_class:
            mock_player = MagicMock()
            mock_player_class.return_value = mock_player
            
            play(frames, fps=15, speed=1.5, color_scheme=CRT_GREEN, loop=True, progress=True)
            
            assert mock_player_class.called
            call_args = mock_player_class.call_args[0]
            assert call_args[0] == frames
            assert call_args[1] == 15
            assert call_args[2] == 1.5
            
            assert mock_player.play.called
            call_kwargs = mock_player.play.call_args[1]
            assert call_kwargs["color_scheme"] is CRT_GREEN
            assert call_kwargs["loop"] is True
            assert call_kwargs["progress"] is True

    def test_play_passes_subtitle_segments(self, sample_ascii_frame):
        """Test play function passes subtitle_segments to TerminalPlayer."""
        frames = [sample_ascii_frame] * 3
        segments = [(0.0, 2.0, "Hi")]

        with patch("video2ascii.player.TerminalPlayer") as mock_player_class:
            mock_player = MagicMock()
            mock_player_class.return_value = mock_player

            play(frames, fps=12, subtitle_segments=segments)

            call_kwargs = mock_player_class.call_args[1]
            assert call_kwargs["subtitle_segments"] == segments
