"""Export ASCII frames as MP4 video."""

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def find_monospace_font() -> Optional[Path]:
    """Try to find a monospace font on the system."""
    logger.debug("Searching for monospace font...")
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
        # VT323 - retro terminal font
        Path.home() / "Library/Fonts/VT323-Regular.ttf",  # macOS user
        Path("/Library/Fonts/VT323-Regular.ttf"),  # macOS system
        Path.home() / ".fonts/VT323-Regular.ttf",  # Linux user
        Path("/usr/share/fonts/truetype/vt323/VT323-Regular.ttf"),  # Linux system
        Path.home() / ".local/share/fonts/VT323-Regular.ttf",  # Linux local
        # IBM Plex Mono - professional monospace
        Path.home() / "Library/Fonts/IBMPlexMono-Regular.ttf",  # macOS user
        Path("/Library/Fonts/IBMPlexMono-Regular.ttf"),  # macOS system
        Path.home() / ".fonts/IBMPlexMono-Regular.ttf",  # Linux user
        Path("/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Regular.ttf"),  # Linux system
        Path.home() / ".local/share/fonts/IBMPlexMono-Regular.ttf",  # Linux local
        Path("/usr/share/fonts/opentype/ibm/plex/IBMPlexMono-Regular.otf"),  # Linux OTF
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
            logger.debug(f"Found monospace font: {font_path}")
            return font_path
    
    logger.warning("No monospace font found, using default")
    return None


def render_ascii_frame(
    ascii_text: str,
    output_path: Path,
    color: bool = False,
    crt: bool = False,
    font_size: int = 20,
    prefer_petscii_font: bool = False,
    prefer_braille_font: bool = False,
    target_width: int = None,
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
    # If braille mode, prioritize bold fonts with braille support, then regular braille fonts
    bold_font_path = None
    use_bold_font = False
    if prefer_braille_font:
        logger.debug("Braille mode: searching for braille-supporting fonts")
        # First try to find a bold braille font
        bold_font_path = find_bold_braille_font()
        if bold_font_path is not None:
            font_path = bold_font_path
            use_bold_font = True
            logger.debug(f"Using bold braille font: {font_path}")
        else:
            logger.debug("No bold braille font found, trying regular braille fonts")
            # Fallback to regular braille font if no bold found
            font_path = find_font_with_braille_support()
            if font_path is None:
                logger.debug("No braille font found, falling back to regular monospace")
                # Fallback to regular font search
                font_path = find_monospace_font()
            else:
                logger.debug(f"Using regular braille font: {font_path}")
    else:
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
            logger.debug(f"Loaded font: {font_path} at size {font_size}")
        except Exception as e:
            logger.warning(f"Failed to load font {font_path}: {e}, using default")
            font = ImageFont.load_default()
    else:
        logger.debug("Using default font")
        font = ImageFont.load_default()
    
    # Calculate image dimensions
    # Get character dimensions
    # For non-monospaced fonts (like Apple Braille), use a reference character
    # and force monospace spacing
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
    
    # Force monospace for braille fonts (Apple Braille is not monospaced)
    # Use a wider spacing to match typical monospace fonts
    if prefer_braille_font and font_path and "Braille" in str(font_path):
        # Force monospace: use a consistent width based on font size
        # Braille characters are naturally narrow, so use wider spacing
        # Typical monospace ratio is ~0.6-0.7 width:height for readability
        char_width = max(char_width, int(font_size * 0.7))
        # Ensure minimum width for readability (braille needs more space)
        char_width = max(char_width, 16)
    
    # Calculate max width, stripping ANSI codes if color is enabled
    # ANSI codes don't take up visual space but affect string length
    if color:
        # Strip ANSI escape sequences when calculating width
        ansi_pattern = re.compile(r'\033\[[0-9;]*m')
        max_width = max(len(ansi_pattern.sub('', line)) for line in lines) if lines else 80
    else:
        max_width = max(len(line) for line in lines) if lines else 80
    num_lines = len(lines)
    
    # Calculate base dimensions using actual character dimensions
    # This preserves the aspect ratio of the ASCII art
    base_width = max_width * char_width
    base_height = num_lines * char_height
    
    # Calculate aspect ratio of the ASCII art
    if num_lines > 0:
        ascii_aspect_ratio = base_width / base_height
    else:
        ascii_aspect_ratio = 1.0
    
    # Determine target width for scaling
    if target_width and target_width > 0:
        target_display_width = target_width
    else:
        # Default: scale to reasonable size (target ~1920px width for HD)
        target_display_width = 1920
    
    # Scale up if base width is smaller than target
    # Preserve aspect ratio when scaling
    if base_width < target_display_width:
        # Calculate scale factor based on width
        scale = target_display_width / base_width
        # Scale font size proportionally
        new_font_size = max(12, int(font_size * scale))
        # Reload font at new size and recalculate character dimensions
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), new_font_size)
                # Recalculate character dimensions with new font
                if hasattr(font, 'getbbox'):
                    bbox = font.getbbox("M")
                    char_width = bbox[2] - bbox[0]
                    char_height = bbox[3] - bbox[1]
                elif hasattr(font, 'getsize'):
                    char_width, char_height = font.getsize("M")
                font_size = new_font_size
            except Exception:
                pass
        
        # Recalculate dimensions with new character size, preserving aspect ratio
        width = max_width * char_width
        height = num_lines * char_height
        
        # Ensure we maintain the same aspect ratio as the original ASCII
        # Recalculate if aspect ratio drifted due to font size changes
        new_aspect = width / height if height > 0 else 1.0
        if abs(new_aspect - ascii_aspect_ratio) > 0.01:  # Allow small floating point differences
            # Adjust height to preserve aspect ratio
            height = int(width / ascii_aspect_ratio) if ascii_aspect_ratio > 0 else height
    else:
        # Already large enough, use base dimensions
        width = base_width
        height = base_height
    
    # Ensure dimensions are even (required for H.264 yuv420p)
    width = width if width % 2 == 0 else width + 1
    height = height if height % 2 == 0 else height + 1
    
    # Scale down if dimensions are too large (H.264 has practical limits)
    # Max reasonable dimensions: 3840x2160 (4K)
    max_dimension = 3840
    if width > max_dimension or height > max_dimension:
        scale = min(max_dimension / width, max_dimension / height)
        width = int(width * scale)
        height = int(height * scale)
        # Re-ensure even after scaling
        width = width if width % 2 == 0 else width + 1
        height = height if height % 2 == 0 else height + 1
        # Scale font size proportionally
        font_size = max(12, int(font_size * scale))
        # Reload font at new size
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), font_size)
                # Recalculate character dimensions
                if hasattr(font, 'getbbox'):
                    bbox = font.getbbox("M")
                    char_width = bbox[2] - bbox[0]
                    char_height = bbox[3] - bbox[1]
                elif hasattr(font, 'getsize'):
                    char_width, char_height = font.getsize("M")
            except Exception:
                pass
    
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
                                # Parse \033[38;2;R;G;Bm format
                                # Split by ';' gives: ['\033[38', '2', 'R', 'G', 'Bm']
                                parts = code.split(";")
                                if len(parts) >= 5:  # Need at least 5 parts: [38, 2, R, G, Bm]
                                    r = int(parts[2])  # R is at index 2
                                    g = int(parts[3])  # G is at index 3
                                    b = int(parts[4].rstrip("m"))  # B is at index 4, strip trailing 'm'
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
                        continue  # Skip to next iteration after parsing ANSI code
                
                # Draw character (this happens AFTER any ANSI code has been parsed)
                char = line[i]
                if char != "\033":
                    # Increase contrast for all MP4 exports to improve detail visibility
                    # For color mode, use lighter contrast boost to preserve color information
                    r, g, b = current_color
                    brightness = (r + g + b) / 3.0
                    
                    if prefer_braille_font and font_path and "Braille" in str(font_path):
                        # Braille in color mode: extra brightness boost due to sparse pixel coverage
                        # Don't darken - brighten dark colors to make them visible
                        # Skip pure black (0,0,0) - it should stay black
                        if r == 0 and g == 0 and b == 0:
                            fill_color = (0, 0, 0)
                        elif brightness < 30:
                            # Extremely dark colors - brighten dramatically
                            boost = 8.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 64:
                            # Very dark colors - brighten significantly
                            boost = 6.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 128:
                            # Dark colors - moderate brightening
                            boost = 4.0
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        else:
                            # Light colors - slight brightening
                            fill_color = (min(255, int(r * 2.0 + 40)), min(255, int(g * 2.0 + 40)), min(255, int(b * 2.0 + 40)))
                    elif color:
                        # Color mode: boost brightness while preserving color ratios
                        # Don't darken already dark colors - instead brighten them significantly
                        # Skip pure black (0,0,0) - it should stay black
                        if r == 0 and g == 0 and b == 0:
                            fill_color = (0, 0, 0)
                        elif brightness < 30:
                            # Extremely dark colors - brighten dramatically to make visible on black background
                            boost = 4.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 64:
                            # Very dark colors - brighten significantly
                            boost = 3.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 128:
                            # Dark colors - moderate brightening
                            boost = 2.2
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        else:
                            # Light colors - slight brightening
                            fill_color = (min(255, int(r * 1.2 + 20)), min(255, int(g * 1.2 + 20)), min(255, int(b * 1.2 + 20)))
                    else:
                        # Grayscale mode: moderate contrast boost (30% increase)
                        if brightness < 128:
                            # Dark colors - make darker for better contrast
                            fill_color = (max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)))
                        else:
                            # Light colors - make lighter for better visibility
                            fill_color = (min(255, int(r * 1.3 + 30)), min(255, int(g * 1.3 + 30)), min(255, int(b * 1.3 + 30)))
                    
                    # For braille without bold font, use stroke effect to simulate bold
                    if prefer_braille_font and not use_bold_font and char != " ":
                        # Draw character multiple times with slight offsets to create bold effect
                        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
                        for offset_x, offset_y in offsets:
                            draw.text((x + offset_x, y + offset_y), char, fill=fill_color, font=font)
                        logger.debug(f"Applied stroke effect to braille character '{char}'")
                    else:
                        draw.text((x, y), char, fill=fill_color, font=font)
                    x += char_width
                
                i += 1
        else:
            # No color - strip ANSI codes and draw the line
            # Remove ANSI escape sequences
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            text_color = crt_green if crt else (255, 255, 255)
            
            # Increase contrast for all MP4 exports to improve detail visibility
            # For color mode, use lighter contrast boost to preserve color information
            r, g, b = text_color
            brightness = (r + g + b) / 3.0
            
            if prefer_braille_font and font_path and "Braille" in str(font_path):
                # Braille in color mode: extra brightness boost due to sparse pixel coverage
                # Don't darken - brighten dark colors to make them visible
                # Skip pure black (0,0,0) - it should stay black
                if r == 0 and g == 0 and b == 0:
                    text_color = (0, 0, 0)
                elif brightness < 30:
                    # Extremely dark colors - brighten dramatically
                    boost = 8.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 64:
                    # Very dark colors - brighten significantly
                    boost = 6.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 128:
                    # Dark colors - moderate brightening
                    boost = 4.0
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                else:
                    # Light colors - slight brightening
                    text_color = (min(255, int(r * 2.0 + 40)), min(255, int(g * 2.0 + 40)), min(255, int(b * 2.0 + 40)))
            elif color:
                # Color mode: boost brightness while preserving color ratios
                # Don't darken already dark colors - instead brighten them significantly
                # Skip pure black (0,0,0) - it should stay black
                if r == 0 and g == 0 and b == 0:
                    text_color = (0, 0, 0)
                elif brightness < 30:
                    # Extremely dark colors - brighten dramatically to make visible on black background
                    boost = 4.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 64:
                    # Very dark colors - brighten significantly
                    boost = 3.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 128:
                    # Dark colors - moderate brightening
                    boost = 2.2
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                else:
                    # Light colors - slight brightening
                    text_color = (min(255, int(r * 1.2 + 20)), min(255, int(g * 1.2 + 20)), min(255, int(b * 1.2 + 20)))
            else:
                # Grayscale mode: moderate contrast boost (30% increase)
                if brightness < 128:
                    text_color = (max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)))
                else:
                    text_color = (min(255, int(r * 1.3 + 30)), min(255, int(g * 1.3 + 30)), min(255, int(b * 1.3 + 30)))
            
            # For braille without bold font, use stroke effect to simulate bold
            if prefer_braille_font and not use_bold_font:
                # Draw line multiple times with slight offsets to create bold effect
                offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
                for offset_x, offset_y in offsets:
                    draw.text((x + offset_x, y + offset_y), clean_line, fill=text_color, font=font)
            else:
                draw.text((x, y), clean_line, fill=text_color, font=font)
        
        y += char_height
    
    img.save(output_path)


def find_font_with_braille_support() -> Optional[Path]:
    """Find a font that supports braille Unicode characters (U+2800-U+28FF).
    
    Prioritizes Apple Braille (macOS built-in) and DejaVu Sans Mono (100% braille coverage).
    """
    logger.debug("Searching for braille-supporting font...")
    # Fonts that typically support braille Unicode
    braille_font_paths = [
        # Apple Braille - macOS built-in, full braille support (100% coverage)
        # Note: These are braille-specific fonts, may not be monospaced
        Path("/System/Library/Fonts/Apple Braille.ttf"),
        Path("/System/Library/Fonts/Apple Braille Outline 8 Dot.ttf"),
        # DejaVu Sans Mono - excellent Unicode support including braille
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        Path.home() / ".fonts/DejaVuSansMono.ttf",
        # Liberation Mono - good Unicode support
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
        # macOS system fonts that support braille
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Courier.ttc"),
        Path("/Library/Fonts/Courier New.ttf"),
        # Iosevka - good Unicode support
        Path.home() / "Library/Fonts/Iosevka-Regular.ttf",
        Path("/Library/Fonts/Iosevka-Regular.ttf"),
        Path.home() / ".fonts/Iosevka-Regular.ttf",
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Regular.ttf"),
    ]
    
    for font_path in braille_font_paths:
        if font_path.exists():
            logger.debug(f"Found braille font: {font_path}")
            return font_path
    
    logger.warning("No braille-supporting font found")
    return None


def find_bold_braille_font() -> Optional[Path]:
    """Find a bold font variant that supports braille Unicode characters.
    
    Searches for bold variants of braille-supporting fonts.
    """
    logger.debug("Searching for bold braille font...")
    # Bold font variants that support braille Unicode
    bold_braille_font_paths = [
        # Apple Braille bold variants (if they exist)
        Path("/System/Library/Fonts/Apple Braille Bold.ttf"),
        Path("/System/Library/Fonts/Apple Braille Outline 8 Dot Bold.ttf"),
        # DejaVu Sans Mono Bold - excellent Unicode support including braille
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf"),
        Path.home() / ".fonts/DejaVuSansMono-Bold.ttf",
        # Liberation Mono Bold
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"),
        # macOS system fonts bold variants
        Path("/System/Library/Fonts/Menlo Bold.ttc"),
        Path("/System/Library/Fonts/Courier Bold.ttc"),
        Path("/Library/Fonts/Courier New Bold.ttf"),
        # Iosevka Bold
        Path.home() / "Library/Fonts/Iosevka-Bold.ttf",
        Path("/Library/Fonts/Iosevka-Bold.ttf"),
        Path.home() / ".fonts/Iosevka-Bold.ttf",
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Bold.ttf"),
    ]
    
    for font_path in bold_braille_font_paths:
        if font_path.exists():
            logger.debug(f"Found bold braille font: {font_path}")
            return font_path
    
    logger.debug("No bold braille font found")
    return None


def export_mp4(
    frames: list[str],
    output_path: Path,
    fps: int,
    color: bool = False,
    crt: bool = False,
    work_dir: Path = None,
    charset: str = "classic",
    target_width: int = 1920,
    codec: str = "h265",
) -> None:
    """Export ASCII frames as MP4 video.
    
    Args:
        frames: List of ASCII art frame strings
        output_path: Path to output MP4 file
        fps: Frames per second
        color: Whether frames contain ANSI color codes
        crt: Apply CRT green phosphor effect
        work_dir: Working directory for temporary rendered images
        charset: Character set name
        target_width: Target width in pixels for rendered frames
        codec: Video codec to use ('h265', 'h264', or 'prores422')
    """
    logger.info(f"Exporting {len(frames)} frames to MP4: {output_path}")
    logger.debug(f"MP4 export settings: fps={fps}, color={color}, crt={crt}, charset={charset}, target_width={target_width}, codec={codec}")
    if work_dir is None:
        work_dir = output_path.parent / f".{output_path.stem}_mp4_temp"
    
    render_dir = work_dir / "rendered"
    render_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Rendering {len(frames)} ASCII frames as images…")
    
    # Render each frame as an image
    prefer_petscii = charset.lower() == "petscii"
    prefer_braille_font = charset.lower() == "braille"
    
    # Warn about braille rendering issues
    if charset.lower() == "braille":
        print("Warning: Braille characters may render as squares in MP4 export.")
        print("  Consider using --charset blocks instead for better MP4 compatibility.")
    
    for i, frame in enumerate(frames):
        if (i + 1) % 10 == 0:
            print(f"  Rendered {i + 1}/{len(frames)} frames…", end="\r")
        
        frame_path = render_dir / f"frame_{i+1:06d}.png"
        render_ascii_frame(
            frame, frame_path, color=color, crt=crt, 
            prefer_petscii_font=prefer_petscii, 
            prefer_braille_font=prefer_braille_font,
            target_width=target_width
        )
    
    print(f"  Rendered {len(frames)}/{len(frames)} frames")
    
    print(f"Creating MP4: {output_path}…")
    
    # Use ffmpeg to create MP4 from rendered images
    pattern = str(render_dir / "frame_%06d.png")
    
    # Build ffmpeg command based on codec
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Overwrite output file
        "-hide_banner",
        "-loglevel", "error",
        "-framerate", str(fps),
        "-i", pattern,
    ]
    
    if codec == "prores422":
        # ProRes 422 HQ encoding
        logger.debug("Using ProRes 422 HQ codec")
        ffmpeg_cmd.extend([
            "-c:v", "prores_ks",
            "-profile:v", "hq",  # High quality profile
            "-pix_fmt", "yuv422p10le",
        ])
    elif codec == "h265":
        # H.265/HEVC encoding
        logger.debug("Using H.265/HEVC codec")
        ffmpeg_cmd.extend([
            "-c:v", "libx265",
            "-pix_fmt", "yuv420p",
            "-crf", "18",  # High quality
            "-preset", "medium",  # Balance between speed and compression
        ])
    else:
        # Default to H.264
        logger.debug("Using H.264 codec")
        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",  # High quality
        ])
    
    ffmpeg_cmd.append(str(output_path))
    
    logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
    subprocess.run(ffmpeg_cmd, check=True)
    
    # Cleanup rendered images
    import shutil
    shutil.rmtree(render_dir, ignore_errors=True)
    
    # Get file size and video dimensions
    size_mb = output_path.stat().st_size / (1024 * 1024)
    
    # Get video dimensions using ffprobe
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=s=x:p=0",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        dimensions = result.stdout.strip()
        if "x" in dimensions:
            width, height = map(int, dimensions.split("x"))
            aspect_ratio = width / height if height > 0 else 0
            print(f"Created: {output_path}")
            print(f"  Size: {size_mb:.2f} MB")
            print(f"  Dimensions: {width}x{height} pixels")
            print(f"  Aspect ratio: {aspect_ratio:.2f}:1")
            print(f"  Frames: {len(frames)} @ {fps} fps")
        else:
            print(f"Created: {output_path} ({size_mb:.2f}MB, {len(frames)} frames @ {fps} fps)")
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        # Fallback if ffprobe fails
        print(f"Created: {output_path} ({size_mb:.2f}MB, {len(frames)} frames @ {fps} fps)")
