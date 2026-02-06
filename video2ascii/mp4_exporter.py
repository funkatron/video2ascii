"""Export ASCII frames as MP4 video."""

import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont


def find_monospace_font() -> Optional[Path]:
    """Try to find a monospace font on the system."""
    # Common font locations
    font_paths = [
        # PetME (KreativeKorp Commodore fonts) - highest priority for PETSCII
        Path.home() / "Library/Fonts/PetMe64.ttf",  # macOS user
        Path("/Library/Fonts/PetMe64.ttf"),  # macOS system
        Path.home() / ".fonts/PetMe64.ttf",  # Linux user
        Path("/usr/share/fonts/truetype/petme/PetMe64.ttf"),  # Linux system
        Path.home() / ".local/share/fonts/PetMe64.ttf",  # Linux local
        # Iosevka - popular monospace font
        Path.home() / "Library/Fonts/Iosevka-Regular.ttf",  # macOS user
        Path("/Library/Fonts/Iosevka-Regular.ttf"),  # macOS system
        Path.home() / ".fonts/Iosevka-Regular.ttf",  # Linux user
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Regular.ttf"),  # Linux system
        Path.home() / ".local/share/fonts/Iosevka-Regular.ttf",  # Linux local
        # macOS system fonts
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Courier.ttc"),
        Path("/Library/Fonts/Courier New.ttf"),
        # Linux system fonts
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        # Windows (if running on WSL or similar)
        Path("/mnt/c/Windows/Fonts/consola.ttf"),
        Path("/mnt/c/Windows/Fonts/cour.ttf"),
    ]
    
    for font_path in font_paths:
        if font_path.exists():
            return font_path
    
    return None


def render_ascii_frame(
    ascii_text: str,
    output_path: Path,
    color: bool = False,
    crt: bool = False,
    font_size: int = 12,
    prefer_petscii_font: bool = False,
) -> None:
    """
    Render ASCII art text as an image.
    
    Args:
        ascii_text: ASCII art string (may contain ANSI color codes if color=True)
        output_path: Path to save rendered image
        color: Whether to parse ANSI color codes
        crt: Apply green phosphor tint
        font_size: Font size in pixels
    """
    lines = ascii_text.split("\n")
    if not lines:
        return
    
    # Find monospace font
    # If PETSCII mode, prioritize PetME fonts
    font_path = find_monospace_font()
    
    # If prefer_petscii_font, try PetME first
    if prefer_petscii_font:
        petscii_fonts = [
            Path.home() / "Library/Fonts/PetMe64.ttf",
            Path("/Library/Fonts/PetMe64.ttf"),
            Path.home() / ".fonts/PetMe64.ttf",
            Path("/usr/share/fonts/truetype/petme/PetMe64.ttf"),
        ]
        for pf in petscii_fonts:
            if pf.exists():
                font_path = pf
                break
    
    if font_path:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()
    
    # Calculate image dimensions
    # Get character dimensions
    try:
        if hasattr(font, 'getbbox'):
            bbox = font.getbbox("M")
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1]
        elif hasattr(font, 'getsize'):
            char_width, char_height = font.getsize("M")
        else:
            char_width, char_height = 8, 16
    except Exception:
        char_width, char_height = 8, 16
    
    max_width = max(len(line) for line in lines) if lines else 80
    width = max_width * char_width
    height = len(lines) * char_height
    
    # Create image with black background
    bg_color = (5, 5, 5) if crt else (0, 0, 0)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    
    # CRT green color
    crt_green = (51, 255, 51)
    
    y = 0
    for line in lines:
        x = 0
        
        if color:
            # Parse ANSI color codes
            i = 0
            current_color = (255, 255, 255)  # Default white
            
            while i < len(line):
                if line[i] == "\033" and i + 1 < len(line) and line[i + 1] == "[":
                    # Find the end of ANSI code
                    end = line.find("m", i)
                    if end != -1:
                        code = line[i:end + 1]
                        # Parse RGB color: \033[38;2;R;G;Bm or reset \033[0m
                        if code == "\033[0m":
                            current_color = (255, 255, 255)
                        elif ";2;" in code:
                            try:
                                parts = code.split(";")
                                if len(parts) >= 6:
                                    r = int(parts[3])
                                    g = int(parts[4])
                                    b = int(parts[5].rstrip("m"))
                                    current_color = (r, g, b)
                                    if crt:
                                        # Apply green tint
                                        current_color = (
                                            min(255, int(r * 0.2 + crt_green[0] * 0.8)),
                                            min(255, int(g * 0.2 + crt_green[1] * 0.8)),
                                            min(255, int(b * 0.2 + crt_green[2] * 0.8)),
                                        )
                            except (ValueError, IndexError):
                                pass
                        i = end + 1
                        continue
                
                # Draw character
                char = line[i]
                if char != "\033":
                    draw.text((x, y), char, fill=current_color, font=font)
                    x += char_width
                
                i += 1
        else:
            # No color - strip ANSI codes and draw the line
            # Remove ANSI escape sequences
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            text_color = crt_green if crt else (255, 255, 255)
            draw.text((x, y), clean_line, fill=text_color, font=font)
        
        y += char_height
    
    img.save(output_path)


def export_mp4(
    frames: list[str],
    output_path: Path,
    fps: int,
    color: bool = False,
    crt: bool = False,
    work_dir: Path = None,
    charset: str = "classic",
) -> None:
    """
    Export ASCII frames as MP4 video.
    
    Args:
        frames: List of ASCII art frame strings
        output_path: Path to output MP4 file
        fps: Frames per second
        color: Whether frames contain ANSI color codes
        crt: Apply CRT green phosphor effect
        work_dir: Working directory for temporary rendered images
    """
    if work_dir is None:
        work_dir = output_path.parent / f".{output_path.stem}_mp4_temp"
    
    render_dir = work_dir / "rendered"
    render_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Rendering {len(frames)} ASCII frames as images…")
    
    # Render each frame as an image
    prefer_petscii = charset.lower() == "petscii"
    for i, frame in enumerate(frames):
        if (i + 1) % 10 == 0:
            print(f"  Rendered {i + 1}/{len(frames)} frames…", end="\r")
        
        frame_path = render_dir / f"frame_{i+1:06d}.png"
        render_ascii_frame(frame, frame_path, color=color, crt=crt, prefer_petscii_font=prefer_petscii)
    
    print(f"  Rendered {len(frames)}/{len(frames)} frames")
    
    print(f"Creating MP4: {output_path}…")
    
    # Use ffmpeg to create MP4 from rendered images
    pattern = str(render_dir / "frame_%06d.png")
    
    subprocess.run(
        [
            "ffmpeg",
            "-y",  # Overwrite output file
            "-hide_banner",
            "-loglevel", "error",
            "-framerate", str(fps),
            "-i", pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",  # High quality
            str(output_path),
        ],
        check=True,
    )
    
    # Cleanup rendered images
    import shutil
    shutil.rmtree(render_dir, ignore_errors=True)
    
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Created: {output_path} ({size_mb:.2f}MB, {len(frames)} frames @ {fps} fps)")
