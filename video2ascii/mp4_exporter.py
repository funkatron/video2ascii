"""Export ASCII frames as MP4 video."""

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from video2ascii.fonts import ResolvedFont, get_subtitle_font_name, resolve_font
from video2ascii.presets import ColorScheme

logger = logging.getLogger(__name__)


def render_ascii_frame(
    ascii_text: str,
    output_path: Path,
    color: bool = False,
    color_scheme: Optional[ColorScheme] = None,
    font_size: int = 20,
    font_path: Optional[Path] = None,
    font_is_bold: bool = False,
    charset: str = "classic",
    target_width: int = None,
) -> None:
    """
    Render ASCII art text as an image.

    Args:
        ascii_text: ASCII art string (may contain ANSI color codes if color=True)
        output_path: Path to save rendered image
        color: Whether to parse ANSI color codes
        color_scheme: Optional ColorScheme for tinted rendering
        font_size: Font size in pixels
        font_path: Pre-resolved font file path (None for Pillow default)
        font_is_bold: Whether font_path is a bold variant (controls braille
                      stroke-effect fallback)
        charset: Character set name (used for braille rendering tweaks)
        target_width: Target width in pixels
    """
    lines = ascii_text.split("\n")
    if not lines:
        return

    is_braille = charset.lower() == "braille"

    if font_path:
        try:
            font = ImageFont.truetype(str(font_path), font_size)
            logger.debug("Loaded font: %s at size %d", font_path, font_size)
        except Exception as e:
            logger.warning("Failed to load font %s: %s, using default", font_path, e)
            font = ImageFont.load_default()
    else:
        logger.debug("Using default font")
        font = ImageFont.load_default()

    # Calculate image dimensions
    # Get character dimensions using a reference character
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
    if is_braille and font_path and "Braille" in str(font_path):
        char_width = max(char_width, int(font_size * 0.7))
        char_width = max(char_width, 16)

    # Calculate max width, stripping ANSI codes if color is enabled
    if color:
        ansi_pattern = re.compile(r'\033\[[0-9;]*m')
        max_width = max(len(ansi_pattern.sub('', line)) for line in lines) if lines else 80
    else:
        max_width = max(len(line) for line in lines) if lines else 80
    num_lines = len(lines)

    # Calculate base dimensions using actual character dimensions
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
        target_display_width = 1920

    # Scale up if base width is smaller than target
    if base_width < target_display_width:
        scale = target_display_width / base_width
        new_font_size = max(12, int(font_size * scale))
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), new_font_size)
                if hasattr(font, 'getbbox'):
                    bbox = font.getbbox("M")
                    char_width = bbox[2] - bbox[0]
                    char_height = bbox[3] - bbox[1]
                elif hasattr(font, 'getsize'):
                    char_width, char_height = font.getsize("M")
                font_size = new_font_size
            except Exception:
                pass

        width = max_width * char_width
        height = num_lines * char_height

        new_aspect = width / height if height > 0 else 1.0
        if abs(new_aspect - ascii_aspect_ratio) > 0.01:
            height = int(width / ascii_aspect_ratio) if ascii_aspect_ratio > 0 else height
    else:
        width = base_width
        height = base_height

    # Ensure dimensions are even (required for H.264 yuv420p)
    width = width if width % 2 == 0 else width + 1
    height = height if height % 2 == 0 else height + 1

    # Scale down if dimensions are too large (4K max)
    max_dimension = 3840
    if width > max_dimension or height > max_dimension:
        scale = min(max_dimension / width, max_dimension / height)
        width = int(width * scale)
        height = int(height * scale)
        width = width if width % 2 == 0 else width + 1
        height = height if height % 2 == 0 else height + 1
        font_size = max(12, int(font_size * scale))
        if font_path:
            try:
                font = ImageFont.truetype(str(font_path), font_size)
                if hasattr(font, 'getbbox'):
                    bbox = font.getbbox("M")
                    char_width = bbox[2] - bbox[0]
                    char_height = bbox[3] - bbox[1]
                elif hasattr(font, 'getsize'):
                    char_width, char_height = font.getsize("M")
            except Exception:
                pass

    bg_color = color_scheme.bg if color_scheme else (0, 0, 0)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    y = 0
    for line in lines:
        x = 0

        if color:
            i = 0
            current_color = (255, 255, 255)

            while i < len(line):
                if line[i] == "\033" and i + 1 < len(line) and line[i + 1] == "[":
                    end = line.find("m", i)
                    if end != -1:
                        code = line[i:end + 1]
                        if code == "\033[0m":
                            current_color = (255, 255, 255)
                        elif ";2;" in code:
                            try:
                                parts = code.split(";")
                                if len(parts) >= 5:
                                    r = int(parts[2])
                                    g = int(parts[3])
                                    b = int(parts[4].rstrip("m"))
                                    current_color = (r, g, b)
                                    if color_scheme:
                                        current_color = color_scheme.blend_color(r, g, b)
                            except (ValueError, IndexError):
                                pass
                        i = end + 1
                        continue

                char = line[i]
                if char != "\033":
                    r, g, b = current_color
                    brightness = (r + g + b) / 3.0

                    if is_braille and font_path and "Braille" in str(font_path):
                        # Braille: extra brightness boost for sparse pixel coverage
                        if r == 0 and g == 0 and b == 0:
                            fill_color = (0, 0, 0)
                        elif brightness < 30:
                            boost = 8.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 64:
                            boost = 6.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 128:
                            boost = 4.0
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        else:
                            fill_color = (min(255, int(r * 2.0 + 40)), min(255, int(g * 2.0 + 40)), min(255, int(b * 2.0 + 40)))
                    elif color:
                        # Color mode: boost brightness preserving ratios
                        if r == 0 and g == 0 and b == 0:
                            fill_color = (0, 0, 0)
                        elif brightness < 30:
                            boost = 4.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 64:
                            boost = 3.5
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        elif brightness < 128:
                            boost = 2.2
                            fill_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                        else:
                            fill_color = (min(255, int(r * 1.2 + 20)), min(255, int(g * 1.2 + 20)), min(255, int(b * 1.2 + 20)))
                    else:
                        # Grayscale mode
                        if brightness < 128:
                            fill_color = (max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)))
                        else:
                            fill_color = (min(255, int(r * 1.3 + 30)), min(255, int(g * 1.3 + 30)), min(255, int(b * 1.3 + 30)))

                    # Braille without bold font: stroke effect to simulate bold
                    if is_braille and not font_is_bold and char != " ":
                        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
                        for offset_x, offset_y in offsets:
                            draw.text((x + offset_x, y + offset_y), char, fill=fill_color, font=font)
                    else:
                        draw.text((x, y), char, fill=fill_color, font=font)
                    x += char_width

                i += 1
        else:
            clean_line = re.sub(r'\033\[[0-9;]*m', '', line)
            text_color = color_scheme.tint if color_scheme else (255, 255, 255)

            r, g, b = text_color
            brightness = (r + g + b) / 3.0

            if is_braille and font_path and "Braille" in str(font_path):
                if r == 0 and g == 0 and b == 0:
                    text_color = (0, 0, 0)
                elif brightness < 30:
                    boost = 8.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 64:
                    boost = 6.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 128:
                    boost = 4.0
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                else:
                    text_color = (min(255, int(r * 2.0 + 40)), min(255, int(g * 2.0 + 40)), min(255, int(b * 2.0 + 40)))
            elif color:
                if r == 0 and g == 0 and b == 0:
                    text_color = (0, 0, 0)
                elif brightness < 30:
                    boost = 4.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 64:
                    boost = 3.5
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                elif brightness < 128:
                    boost = 2.2
                    text_color = (min(255, int(r * boost)), min(255, int(g * boost)), min(255, int(b * boost)))
                else:
                    text_color = (min(255, int(r * 1.2 + 20)), min(255, int(g * 1.2 + 20)), min(255, int(b * 1.2 + 20)))
            else:
                if brightness < 128:
                    text_color = (max(0, int(r * 0.5)), max(0, int(g * 0.5)), max(0, int(b * 0.5)))
                else:
                    text_color = (min(255, int(r * 1.3 + 30)), min(255, int(g * 1.3 + 30)), min(255, int(b * 1.3 + 30)))

            # Braille without bold font: stroke effect to simulate bold
            if is_braille and not font_is_bold:
                offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 0), (0, 1), (1, -1), (1, 0), (1, 1)]
                for offset_x, offset_y in offsets:
                    draw.text((x + offset_x, y + offset_y), clean_line, fill=text_color, font=font)
            else:
                draw.text((x, y), clean_line, fill=text_color, font=font)

        y += char_height

    img.save(output_path)


def _escape_ffmpeg_path(path: Path) -> str:
    """
    Escape a file path for use inside an ffmpeg filter expression.

    ffmpeg filter syntax treats backslash, colon, and single-quote as special.

    Args:
        path: File path to escape.

    Returns:
        Escaped path string safe for use in -vf filters.
    """
    s = str(path)
    s = s.replace("\\", "\\\\")
    s = s.replace(":", "\\:")
    s = s.replace("'", "\\'")
    return s


def export_mp4(
    frames: list[str],
    output_path: Path,
    fps: int,
    color: bool = False,
    color_scheme: Optional[ColorScheme] = None,
    work_dir: Path = None,
    charset: str = "classic",
    target_width: int = 1920,
    codec: str = "h265",
    subtitle_path: Optional[Path] = None,
    font_override: Optional[str] = None,
) -> None:
    """Export ASCII frames as MP4 video.

    Args:
        frames: List of ASCII art frame strings
        output_path: Path to output MP4 file
        fps: Frames per second
        color: Whether frames contain ANSI color codes
        color_scheme: Optional ColorScheme for tinted rendering
        work_dir: Working directory for temporary rendered images
        charset: Character set name
        target_width: Target width in pixels for rendered frames
        codec: Video codec to use ('h265', 'h264', or 'prores422')
        subtitle_path: Optional path to SRT file to burn into video
        font_override: Optional font name or path for rendering
    """
    logger.info("Exporting %d frames to MP4: %s", len(frames), output_path)
    logger.debug(
        "MP4 export settings: fps=%d, color=%s, color_scheme=%s, charset=%s, "
        "target_width=%d, codec=%s, font_override=%s",
        fps, color, color_scheme, charset, target_width, codec, font_override,
    )

    # Resolve font once for all frames
    resolved = resolve_font(charset, font_override)
    if resolved.path:
        logger.info("Rendering font: %s (bold=%s)", resolved.path.name, resolved.is_bold)

    if work_dir is None:
        work_dir = output_path.parent / f".{output_path.stem}_mp4_temp"

    render_dir = work_dir / "rendered"
    render_dir.mkdir(parents=True, exist_ok=True)

    print(f"Rendering {len(frames)} ASCII frames as images…")

    # Warn about braille rendering issues
    if charset.lower() == "braille":
        print("Warning: Braille characters may render as squares in MP4 export.")
        print("  Consider using --charset blocks instead for better MP4 compatibility.")

    for i, frame in enumerate(frames):
        if (i + 1) % 10 == 0:
            print(f"  Rendered {i + 1}/{len(frames)} frames…", end="\r")

        frame_path = render_dir / f"frame_{i+1:06d}.png"
        render_ascii_frame(
            frame,
            frame_path,
            color=color,
            color_scheme=color_scheme,
            font_path=resolved.path,
            font_is_bold=resolved.is_bold,
            charset=charset,
            target_width=target_width,
        )

    print(f"  Rendered {len(frames)}/{len(frames)} frames")

    print(f"Creating MP4: {output_path}…")

    # Use ffmpeg to create MP4 from rendered images
    pattern = str(render_dir / "frame_%06d.png")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-framerate", str(fps),
        "-i", pattern,
    ]

    if codec == "prores422":
        logger.debug("Using ProRes 422 HQ codec")
        ffmpeg_cmd.extend([
            "-c:v", "prores_ks",
            "-profile:v", "hq",
            "-pix_fmt", "yuv422p10le",
        ])
    elif codec == "h265":
        logger.debug("Using H.265/HEVC codec")
        ffmpeg_cmd.extend([
            "-c:v", "libx265",
            "-tag:v", "hvc1",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
            "-preset", "medium",
        ])
    else:
        logger.debug("Using H.264 codec")
        ffmpeg_cmd.extend([
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "18",
        ])

    # Burn subtitles into video if SRT path is provided
    if subtitle_path and subtitle_path.exists():
        escaped_path = _escape_ffmpeg_path(subtitle_path)
        font_name = get_subtitle_font_name()
        subtitle_filter = (
            f"subtitles={escaped_path}"
            f":force_style='Fontname={font_name},FontSize=24"
            f",PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2'"
        )
        ffmpeg_cmd.extend(["-vf", subtitle_filter])
        logger.info("Burning subtitles into MP4: %s (font: %s)", subtitle_path.name, font_name)

    ffmpeg_cmd.append(str(output_path))

    logger.debug("FFmpeg command: %s", " ".join(ffmpeg_cmd))
    subprocess.run(ffmpeg_cmd, check=True)

    # Cleanup rendered images
    import shutil
    shutil.rmtree(render_dir, ignore_errors=True)

    # Get file size and video dimensions
    size_mb = output_path.stat().st_size / (1024 * 1024)

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
        print(f"Created: {output_path} ({size_mb:.2f}MB, {len(frames)} frames @ {fps} fps)")
