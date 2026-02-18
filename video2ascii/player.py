"""Terminal playback engine."""

import os
import signal
import sys
import time
from typing import Optional

from video2ascii.presets import ColorScheme
from video2ascii.subtitle import get_subtitle_for_frame


# ANSI escape codes
CURSOR_HOME = "\033[H"
CURSOR_HIDE = "\033[?25l"
CURSOR_SHOW = "\033[?25h"
CLEAR_SCREEN = "\033[2J"
CLEAR_LINE = "\033[K"
RESET = "\033[0m"


def _ansi_fg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit foreground color escape sequence."""
    return f"\033[38;2;{r};{g};{b}m"


def _ansi_bg(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit background color escape sequence."""
    return f"\033[48;2;{r};{g};{b}m"


class TerminalPlayer:
    """Plays ASCII frames in the terminal."""
    
    def __init__(
        self,
        frames: list[str],
        fps: int,
        speed: float = 1.0,
        subtitle_segments: Optional[list[tuple[float, float, str]]] = None,
    ):
        self.frames = frames
        self.fps = fps
        self.speed = speed
        self.frame_delay = 1.0 / (fps * speed)
        self.interrupted = False
        self.subtitle_segments = subtitle_segments
        
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
    
    def draw_progress(
        self,
        current: int,
        total: int,
        color_scheme: Optional[ColorScheme] = None,
    ):
        """Draw progress bar at bottom of screen."""
        width = 40
        pct = int((current * 100) / total)
        filled = int((current * width) / total)
        empty = width - filled
        
        print("\033[999;1H", end="", flush=True)
        print(CLEAR_LINE, end="", flush=True)
        
        if color_scheme:
            print(_ansi_fg(*color_scheme.tint), end="", flush=True)
        
        bar = "[" + "=" * filled + " " * empty + "]"
        print(f"{bar} {pct:3d}% ({current}/{total})", end="", flush=True)
        
        if color_scheme:
            print(RESET, end="", flush=True)
    
    def _draw_subtitle(
        self,
        frame_index: int,
        color_scheme: Optional[ColorScheme],
        progress: bool,
    ):
        """Draw subtitle text pinned to the bottom of the terminal."""
        subtitle_text = get_subtitle_for_frame(
            self.subtitle_segments, frame_index, self.fps,
        )

        row = "998" if progress else "999"
        print(f"\033[{row};1H", end="", flush=True)
        print(CLEAR_LINE, end="", flush=True)

        if subtitle_text:
            try:
                cols = os.get_terminal_size().columns
            except OSError:
                cols = 80
            padding = max(0, (cols - len(subtitle_text)) // 2)

            if color_scheme:
                print(_ansi_fg(*color_scheme.tint), end="", flush=True)
            print(" " * padding + subtitle_text, end="", flush=True)
            if color_scheme:
                print(RESET, end="", flush=True)
    
    def play(
        self,
        color_scheme: Optional[ColorScheme] = None,
        loop: bool = False,
        progress: bool = False,
    ):
        """Play frames.

        Args:
            color_scheme: Optional ColorScheme for tinted rendering.
            loop: Loop playback forever.
            progress: Show progress bar.
        """
        print(CURSOR_HIDE, end="", flush=True)
        
        if color_scheme:
            print(_ansi_bg(*color_scheme.bg), end="", flush=True)
        
        print(CLEAR_SCREEN, end="", flush=True)
        
        try:
            while True:
                for i, frame in enumerate(self.frames):
                    if self.interrupted:
                        return
                    
                    print(CURSOR_HOME, end="", flush=True)
                    
                    if color_scheme:
                        print(_ansi_fg(*color_scheme.tint), end="", flush=True)
                    
                    print(frame, end="", flush=True)
                    
                    if color_scheme:
                        print(RESET, end="", flush=True)
                    
                    if self.subtitle_segments:
                        self._draw_subtitle(i, color_scheme, progress)
                    
                    if progress:
                        self.draw_progress(i + 1, len(self.frames), color_scheme)
                    
                    time.sleep(self.frame_delay)
                
                if not loop:
                    break
                
                print(CURSOR_HOME, end="", flush=True)
        
        finally:
            self.cleanup()


def play(
    frames: list[str],
    fps: int,
    speed: float = 1.0,
    color_scheme: Optional[ColorScheme] = None,
    loop: bool = False,
    progress: bool = False,
    subtitle_segments: Optional[list[tuple[float, float, str]]] = None,
) -> None:
    """Play ASCII frames in terminal.

    Args:
        frames: List of ASCII art frame strings.
        fps: Original frames per second.
        speed: Playback speed multiplier.
        color_scheme: Optional ColorScheme for tinted rendering.
        loop: Loop playback forever.
        progress: Show progress bar.
        subtitle_segments: Parsed SRT segments for subtitle display.
    """
    player = TerminalPlayer(frames, fps, speed, subtitle_segments=subtitle_segments)
    player.play(color_scheme=color_scheme, loop=loop, progress=progress)
