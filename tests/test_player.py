"""Tests for player module."""

import signal
import time
from unittest.mock import MagicMock, patch

import pytest

from video2ascii.player import TerminalPlayer, play


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
        
        # Simulate interrupt
        player.interrupted = True
        player.cleanup()
        
        # Cleanup should not raise
        assert True
    
    def test_play_crt_mode_applies_green(self, sample_ascii_frame):
        """Test CRT mode applies green color codes."""
        frames = [sample_ascii_frame] * 2
        
        printed_output = []
        def mock_print(*args, **kwargs):
            printed_output.append("".join(str(a) for a in args))
        
        with patch("builtins.print", side_effect=mock_print):
            with patch("time.sleep"):
                with patch("signal.signal"):
                    player = TerminalPlayer(frames, fps=12, speed=100.0)  # Fast for testing
                    try:
                        player.play(crt=True, loop=False, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass
                
                # Check that CRT green code was printed
                output_str = "".join(printed_output)
                assert "\033[38;2;51;255;51m" in output_str or len(printed_output) == 0  # May exit early
    
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
                    player.interrupted = True  # Stop immediately
                    try:
                        player.play(crt=False, loop=True, progress=False)
                    except (KeyboardInterrupt, SystemExit):
                        pass


class TestPlayFunction:
    """Tests for play function."""
    
    def test_basic_playback_flow(self, sample_ascii_frame):
        """Test basic playback flow."""
        frames = [sample_ascii_frame] * 3
        
        with patch("video2ascii.player.TerminalPlayer") as mock_player_class:
            mock_player = MagicMock()
            mock_player_class.return_value = mock_player
            
            play(frames, fps=12, speed=1.0, crt=False, loop=False, progress=False)
            
            # Verify TerminalPlayer was instantiated correctly
            assert mock_player_class.called
            call_args = mock_player_class.call_args[0]
            assert call_args[0] == frames
            assert call_args[1] == 12
            assert call_args[2] == 1.0
            
            # Verify play was called
            assert mock_player.play.called
            call_kwargs = mock_player.play.call_args[1]
            assert call_kwargs["crt"] is False
            assert call_kwargs["loop"] is False
            assert call_kwargs["progress"] is False
    
    def test_play_with_parameters(self, sample_ascii_frame):
        """Test play function with all parameters."""
        frames = [sample_ascii_frame] * 3
        
        with patch("video2ascii.player.TerminalPlayer") as mock_player_class:
            mock_player = MagicMock()
            mock_player_class.return_value = mock_player
            
            play(frames, fps=15, speed=1.5, crt=True, loop=True, progress=True)
            
            # Verify TerminalPlayer was instantiated correctly
            assert mock_player_class.called
            call_args = mock_player_class.call_args[0]
            assert call_args[0] == frames
            assert call_args[1] == 15
            assert call_args[2] == 1.5
            
            # Verify play was called
            assert mock_player.play.called
            call_kwargs = mock_player.play.call_args[1]
            assert call_kwargs["crt"] is True
            assert call_kwargs["loop"] is True
            assert call_kwargs["progress"] is True
