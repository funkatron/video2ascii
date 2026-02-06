"""Frame extraction and ASCII conversion."""

import logging
import subprocess
import sys
from pathlib import Path
from multiprocessing import Pool
from typing import Optional

from PIL import Image, ImageFilter, ImageEnhance

logger = logging.getLogger(__name__)


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
    logger.debug(f"Extracting frames from {input_path} (fps={fps}, width={width}, crt={crt})")
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(exist_ok=True)
    
    # Build ffmpeg filter chain
    filters = [f"fps={fps}", f"scale={width}:-1"]
    
    if crt:
        # Add slight blur and boost contrast for CRT feel
        filters.append("unsharp=5:5:1.5:5:5:0.0")
        logger.debug("Added CRT enhancement filter (unsharp)")
    
    filter_chain = ",".join(filters)
    output_pattern = str(frames_dir / "frame_%06d.png")
    logger.debug(f"FFmpeg filter chain: {filter_chain}")
    logger.debug(f"Output pattern: {output_pattern}")
    
    # Extract frames
    logger.debug("Running ffmpeg to extract frames...")
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
    logger.debug(f"Extracted {len(frame_files)} frames")
    return frame_files


# Predefined character sets
CHARSETS = {
    "classic": " .:-=+*#%@",  # Default - balanced
    "blocks": " ░▒▓█",  # Unicode block characters - bold, chunky
    "braille": " ⠁⠂⠃⠄⠅⠆⠇⠈⠉⠊⠋⠌⠍⠎⠏⠐⠑⠒⠓⠔⠕⠖⠗⠘⠙⠚⠛⠜⠝⠞⠟⠠⠡⠢⠣⠤⠥⠦⠧⠨⠩⠪⠫⠬⠭⠮⠯⠰⠱⠲⠳⠴⠵⠶⠷⠸⠹⠺⠻⠼⠽⠾⠿",  # Braille - high resolution
    "dense": " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",  # Many characters - detailed
    "simple": " .oO0",  # Minimal - clean
    # True PETSCII graphics characters (from PETSCII $A0-$DF, screen codes $60-$7F)
    # Using Unicode mappings from KreativeKorp PETSCII standard
    # Using widely-supported Unicode block characters (avoiding Unicode 13.0+ if needed)
    # Ordered by brightness/density for ASCII art conversion
    "petscii": (
        " "  # Space (lightest)
        "\u2591"  # LIGHT SHADE
        "\u2581"  # LOWER ONE EIGHTH BLOCK
        "\u258F"  # LEFT ONE EIGHTH BLOCK  
        "\u2594"  # UPPER ONE EIGHTH BLOCK
        "\u258E"  # LEFT ONE QUARTER BLOCK
        "\u2582"  # LOWER ONE QUARTER BLOCK
        "\u2595"  # RIGHT ONE EIGHTH BLOCK
        "\u258D"  # LEFT THREE EIGHTHS BLOCK
        "\u2583"  # LOWER THREE EIGHTHS BLOCK
        "\u258C"  # LEFT HALF BLOCK
        "\u2584"  # LOWER HALF BLOCK
        "\u2592"  # MEDIUM SHADE
        "\u2593"  # DARK SHADE
        "\u2597"  # QUADRANT LOWER RIGHT
        "\u2596"  # QUADRANT LOWER LEFT
        "\u2598"  # QUADRANT UPPER LEFT
        "\u259D"  # QUADRANT UPPER RIGHT
        "\u259A"  # QUADRANT UPPER LEFT AND LOWER RIGHT
        "\u2599"  # QUADRANT UPPER LEFT AND LOWER LEFT AND LOWER RIGHT
        "\u259B"  # QUADRANT UPPER LEFT AND UPPER RIGHT AND LOWER LEFT
        "\u259C"  # QUADRANT UPPER LEFT AND UPPER RIGHT AND LOWER RIGHT
        "\u2589"  # LEFT SEVEN EIGHTHS BLOCK
        "\u258A"  # LEFT THREE QUARTERS BLOCK
        "\u258B"  # LEFT FIVE EIGHTHS BLOCK
        "\u2586"  # LOWER SEVEN EIGHTHS BLOCK
        "\u2587"  # LOWER FIVE EIGHTHS BLOCK
        "\u2585"  # LOWER THREE QUARTERS BLOCK
        "\u2588"  # FULL BLOCK (darkest)
    ),
}


def image_to_ascii(
    img: Image.Image, width: int, color: bool = False, invert: bool = False, aspect_ratio: float = 1.2, charset: str = "classic"
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
    # Get character set
    if charset in CHARSETS:
        chars = CHARSETS[charset]
    else:
        # Custom charset provided as string
        chars = charset
    
    if invert:
        chars = chars[::-1]
    
    # Calculate aspect ratio correction
    # Terminal characters are typically taller than wide (varies by font/terminal)
    # Lower values (1.0-1.3) produce shorter output, higher values (1.5-2.0) preserve more height
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


def detect_edges(img: Image.Image, color: bool = False, threshold: float = 0.15) -> Image.Image:
    """
    Improved edge detection using multiple techniques for cleaner edges.
    
    Args:
        img: Input PIL Image
        color: If True, preserve color information from original
        threshold: Edge strength threshold (0.0-1.0), higher = fewer edges
        
    Returns:
        Edge-detected image
    """
    # Convert to grayscale for edge detection
    gray = img.convert("L")
    
    # Apply Gaussian blur to reduce noise
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=1.0))
    
    # Use FIND_EDGES filter (Sobel-based)
    edges = blurred.filter(ImageFilter.FIND_EDGES)
    
    # Enhance contrast to make edges more prominent
    enhancer = ImageEnhance.Contrast(edges)
    edges = enhancer.enhance(2.0)  # Increase contrast
    
    # Apply threshold to keep only strong edges
    threshold_value = int(threshold * 255)
    edges_array = edges.load()
    width, height = edges.size
    
    for y in range(height):
        for x in range(width):
            pixel = edges_array[x, y]
            if pixel < threshold_value:
                edges_array[x, y] = 0
            else:
                # Enhance bright edges
                edges_array[x, y] = min(255, int(pixel * 1.3))
    
    # If color mode, blend edges with original image colors
    if color:
        rgb_original = img.convert("RGB")
        rgb_edges = edges.convert("RGB")
        
        # Blend: use edge brightness to modulate original colors
        original_pixels = rgb_original.load()
        edge_pixels = rgb_edges.load()
        result = Image.new("RGB", img.size)
        result_pixels = result.load()
        
        for y in range(height):
            for x in range(width):
                # Get edge strength (brightness of edge pixel)
                edge_r, edge_g, edge_b = edge_pixels[x, y]
                edge_strength = (edge_r + edge_g + edge_b) / 3.0 / 255.0
                
                # Get original color
                orig_r, orig_g, orig_b = original_pixels[x, y]
                
                # Blend: stronger edges get more color, weak edges are dark
                result_pixels[x, y] = (
                    int(orig_r * edge_strength),
                    int(orig_g * edge_strength),
                    int(orig_b * edge_strength),
                )
        
        return result
    else:
        return edges


def convert_frame(args: tuple) -> tuple[int, str]:
    """Convert a single frame to ASCII (called by multiprocessing)."""
    """
    Convert a single frame to ASCII (for parallel processing).
    
    Args:
        args: Tuple of (frame_path, width, color, invert, edge, aspect_ratio, edge_threshold, charset)
        
    Returns:
        Tuple of (frame_number, ascii_string)
    """
    frame_path, width, color, invert, edge, aspect_ratio, edge_threshold, charset = args
    
    # Load image
    img = Image.open(frame_path)
    
    # Apply improved edge detection if requested
    if edge:
        img = detect_edges(img, color=color, threshold=edge_threshold)
    
    # Convert to ASCII
    ascii_art = image_to_ascii(img, width, color, invert, aspect_ratio, charset)
    
    # Extract frame number from filename
    frame_num = int(frame_path.stem.split("_")[1])
    
    return frame_num, ascii_art


def convert_all(
    frame_paths: list[Path],
    width: int,
    color: bool = False,
    invert: bool = False,
    edge: bool = False,
    aspect_ratio: float = 1.2,
    edge_threshold: float = 0.15,
    charset: str = "classic",
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
    logger.debug(f"Converting {len(frame_paths)} frames (width={width}, color={color}, "
                 f"invert={invert}, edge={edge}, charset={charset}, aspect_ratio={aspect_ratio})")
    
    # Prepare arguments for parallel processing
    args_list = [
        (path, width, color, invert, edge, aspect_ratio, edge_threshold, charset)
        for path in frame_paths
    ]
    
    # Convert in parallel
    # Use 'fork' on Unix systems if available, fallback to 'spawn' on macOS
    # This avoids issues when the module is imported or run from stdin
    import multiprocessing
    try:
        # Try to use fork if available (faster, works better with imports)
        ctx = multiprocessing.get_context('fork')
        logger.debug("Using multiprocessing context: fork")
    except ValueError:
        # Fallback to spawn (required on macOS, but needs proper __main__ protection)
        ctx = multiprocessing.get_context('spawn')
        logger.debug("Using multiprocessing context: spawn")
    
    logger.debug(f"Starting parallel conversion with {ctx.cpu_count()} workers")
    with ctx.Pool() as pool:
        results = pool.map(convert_frame, args_list)
    
    # Sort by frame number and return ASCII strings
    results.sort(key=lambda x: x[0])
    logger.debug(f"Completed conversion of {len(results)} frames")
    return [ascii_str for _, ascii_str in results]
