"""Terminal playback engine."""

import os
import signal
import sys
import time
from typing import Optional

from video2ascii.subtitle import get_subtitle_for_frame


# ANSI escape codes
CURSOR_HOME = "\033[H"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"
CLEAR_SCREEN = "\033[2J"
CLEAR_LINE = "\033[K"
RESET = "\033[0m"

# CRT colors
CRT_GREEN = "\033[38;2;51;255;51m"
CRT_BG = "\033[48;2;5;5;5m"


class TerminalPlayer:
    """Plays ASCII frames in the terminal."""
    
    def __init__(
        self,
        frames: list[str],
        fps: int,
        speed: float = 1.0,
        subtitle_segments: Optional[list[tuple[float, float, str]]] = None,
    ):
        """
        Initialize player.
        
        Args:
            frames: List of ASCII art frame strings
            fps: Original frames per second
            speed: Playback speed multiplier
            subtitle_segments: Parsed SRT segments for subtitle display
        """
        self.frames = frames
        self.fps = fps
        self.speed = speed
        self.frame_delay = 1.0 / (fps * speed)
        self.interrupted = False
        self.subtitle_segments = subtitle_segments
        
        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.interrupted = True
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Restore terminal state."""
        print(CURSOR_SHOW, end="", flush=True)
        print(RESET, end="", flush=True)
    
    def draw_progress(self, current: int, total: int, crt: bool = False):
        """
        Draw progress bar at bottom of screen.
        
        Args:
            current: Current frame number (1-indexed)
            total: Total number of frames
            crt: Use CRT green color
        """
        width = 40
        pct = int((current * 100) / total)
        filled = int((current * width) / total)
        empty = width - filled
        
        # Move to bottom of screen
        print("\033[999;1H", end="", flush=True)
        print(CLEAR_LINE, end="", flush=True)
        
        if crt:
            print(CRT_GREEN, end="", flush=True)
        
        bar = "[" + "=" * filled + " " * empty + "]"
        print(f"{bar} {pct:3d}% ({current}/{total})", end="", flush=True)
        
        if crt:
            print(RESET, end="", flush=True)
    
    def _draw_subtitle(self, frame_index: int, crt: bool, progress: bool):
        """
        Draw subtitle text pinned to the bottom of the terminal.

        Places the subtitle on the second-to-last row when a progress bar
        is shown, or on the last row otherwise.

        Args:
            frame_index: Current frame index (0-based).
            crt: Use CRT green color.
            progress: Whether the progress bar is also being drawn.
        """
        subtitle_text = get_subtitle_for_frame(
            self.subtitle_segments, frame_index, self.fps,
        )

        # Row: second-to-last if progress bar present, otherwise last
        row = "998" if progress else "999"
        print(f"\033[{row};1H", end="", flush=True)
        print(CLEAR_LINE, end="", flush=True)

        if subtitle_text:
            # Get terminal width for centering
            try:
                cols = os.get_terminal_size().columns
            except OSError:
                cols = 80
            padding = max(0, (cols - len(subtitle_text)) // 2)

            if crt:
                print(CRT_GREEN, end="", flush=True)
            print(" " * padding + subtitle_text, end="", flush=True)
            if crt:
                print(RESET, end="", flush=True)
    
    def play(
        self,
        crt: bool = False,
        loop: bool = False,
        progress: bool = False,
    ):
        """
        Play frames.
        
        Args:
            crt: Enable CRT green phosphor mode
            loop: Loop playback forever
            progress: Show progress bar
        """
        # Hide cursor and clear screen
        print(CURSOR_HIDE, end="", flush=True)
        
        if crt:
            print(CRT_BG, end="", flush=True)
        
        print(CLEAR_SCREEN, end="", flush=True)
        
        try:
            while True:
                for i, frame in enumerate(self.frames):
                    if self.interrupted:
                        return
                    
                    # Move cursor home and display frame
                    print(CURSOR_HOME, end="", flush=True)
                    
                    if crt:
                        print(CRT_GREEN, end="", flush=True)
                    
                    print(frame, end="", flush=True)
                    
                    if crt:
                        print(RESET, end="", flush=True)
                    
                    # Draw subtitle if available (pinned to bottom of terminal)
                    if self.subtitle_segments:
                        self._draw_subtitle(i, crt, progress)
                    
                    # Draw progress if requested
                    if progress:
                        self.draw_progress(i + 1, len(self.frames), crt)
                    
                    # Sleep for frame duration
                    time.sleep(self.frame_delay)
                
                # Exit if not looping
                if not loop:
                    break
                
                # Reset for next loop
                print(CURSOR_HOME, end="", flush=True)
        
        finally:
            self.cleanup()


def play(
    frames: list[str],
    fps: int,
    speed: float = 1.0,
    crt: bool = False,
    loop: bool = False,
    progress: bool = False,
    subtitle_segments: Optional[list[tuple[float, float, str]]] = None,
) -> None:
    """
    Play ASCII frames in terminal.
    
    Args:
        frames: List of ASCII art frame strings
        fps: Original frames per second
        speed: Playback speed multiplier
        crt: Enable CRT green phosphor mode
        loop: Loop playback forever
        progress: Show progress bar
        subtitle_segments: Parsed SRT segments for subtitle display
    """
    player = TerminalPlayer(frames, fps, speed, subtitle_segments=subtitle_segments)
    player.play(crt=crt, loop=loop, progress=progress)
