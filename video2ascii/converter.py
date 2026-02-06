"""Frame extraction and ASCII conversion."""

import subprocess
import sys
from pathlib import Path
from multiprocessing import Pool
from typing import Optional

from PIL import Image, ImageFilter


def check_ffmpeg() -> None:
    """Check if ffmpeg is available."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg not found. Please install ffmpeg:", file=sys.stderr)
        print("  macOS: brew install ffmpeg", file=sys.stderr)
        print("  Linux: apt install ffmpeg (or equivalent)", file=sys.stderr)
        sys.exit(1)


def extract_frames(
    input_path: Path, fps: int, width: int, work_dir: Path, crt: bool = False
) -> list[Path]:
    """
    Extract frames from video using ffmpeg.
    
    Args:
        input_path: Path to input video file
        fps: Target frames per second
        width: Target width in characters
        work_dir: Working directory for frame storage
        edge: Apply edge detection filter
        crt: Apply CRT enhancement filter
        
    Returns:
        List of paths to extracted frame PNG files
    """
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    
    # Build ffmpeg filter chain
    filters = [f"fps={fps}", f"scale={width}:-1"]
    
    if crt:
        # Add slight blur and boost contrast for CRT feel
        filters.append("unsharp=5:5:1.5:5:5:0.0")
    
    filter_chain = ",".join(filters)
    output_pattern = str(frames_dir / "frame_%06d.png")
    
    # Extract frames
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(input_path),
            "-vf", filter_chain,
            output_pattern,
        ],
        check=True,
    )
    
    # Return sorted list of frame files
    frame_files = sorted(frames_dir.glob("frame_*.png"))
    return frame_files


def image_to_ascii(
    img: Image.Image, width: int, color: bool = False, invert: bool = False
) -> str:
    """
    Convert PIL Image to ASCII art.
    
    Args:
        img: PIL Image object
        width: Target width in characters
        color: Enable ANSI color output
        invert: Invert brightness
        
    Returns:
        ASCII art string
    """
    # Character density ramp (dark to light)
    chars = " .:-=+*#%@"
    if invert:
        chars = chars[::-1]
    
    # Calculate aspect ratio correction
    # Terminal characters are roughly 2:1 height:width
    aspect_ratio = 2.0
    height = int(img.height * aspect_ratio * width / img.width)
    
    # Resize image
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    
    # Convert to grayscale if not using color
    if not color:
        img = img.convert("L")
    
    lines = []
    pixels = img.load()
    
    for y in range(img.height):
        line = ""
        for x in range(img.width):
            if color:
                r, g, b = pixels[x, y][:3]
                # Map to character based on brightness
                brightness = (r + g + b) / 3.0
                char_idx = int((brightness / 255.0) * (len(chars) - 1))
                char = chars[char_idx]
                # Add ANSI color code
                line += f"\033[38;2;{r};{g};{b}m{char}\033[0m"
            else:
                # Grayscale
                brightness = pixels[x, y]
                char_idx = int((brightness / 255.0) * (len(chars) - 1))
                line += chars[char_idx]
        lines.append(line)
    
    return "\n".join(lines)


def convert_frame(args: tuple) -> tuple[int, str]:
    """
    Convert a single frame to ASCII (for parallel processing).
    
    Args:
        args: Tuple of (frame_path, width, color, invert, edge)
        
    Returns:
        Tuple of (frame_number, ascii_string)
    """
    frame_path, width, color, invert, edge = args
    
    # Load image
    img = Image.open(frame_path)
    
    # Apply edge detection if requested (in Python, not ffmpeg)
    if edge:
        # Convert to grayscale, apply edge filter, then back to RGB for color mode
        img_gray = img.convert("L")
        img_edges = img_gray.filter(ImageFilter.FIND_EDGES)
        if color:
            img = img_edges.convert("RGB")
        else:
            img = img_edges
    
    # Convert to ASCII
    ascii_art = image_to_ascii(img, width, color, invert)
    
    # Extract frame number from filename
    frame_num = int(frame_path.stem.split("_")[1])
    
    return frame_num, ascii_art


def convert_all(
    frame_paths: list[Path],
    width: int,
    color: bool = False,
    invert: bool = False,
    edge: bool = False,
) -> list[str]:
    """
    Convert all frames to ASCII in parallel.
    
    Args:
        frame_paths: List of paths to frame images
        width: Target width in characters
        color: Enable ANSI color output
        invert: Invert brightness
        edge: Apply edge detection
        
    Returns:
        List of ASCII art strings, sorted by frame number
    """
    # Prepare arguments for parallel processing
    args_list = [
        (path, width, color, invert, edge)
        for path in frame_paths
    ]
    
    # Convert in parallel
    with Pool() as pool:
        results = pool.map(convert_frame, args_list)
    
    # Sort by frame number and return ASCII strings
    results.sort(key=lambda x: x[0])
    return [ascii_str for _, ascii_str in results]
