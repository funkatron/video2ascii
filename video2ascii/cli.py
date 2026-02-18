"""Command-line interface."""

import argparse
import logging
import sys
import tempfile
from pathlib import Path

from video2ascii import __version__
from video2ascii.converter import check_ffmpeg, extract_frames, convert_all, CHARSETS
from video2ascii.exporter import export
from video2ascii.mp4_exporter import export_mp4
from video2ascii.player import play
from video2ascii.presets import PRESETS, ColorScheme, CRT_GREEN

# Set up logging
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert videos to ASCII art and play in terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s input.mp4
  %(prog)s input.mp4 --width 160 --fps 12
  %(prog)s input.mp4 --color
  %(prog)s input.mp4 --preset crt
  %(prog)s input.mp4 --preset c64
  %(prog)s input.mp4 --crt
  %(prog)s input.mp4 --edge --invert
  %(prog)s input.mp4 --loop --speed 1.5 --progress
  %(prog)s input.mp4 --export movie.sh
  %(prog)s input.mp4 --subtitle
  %(prog)s input.mp4 --subtitle --export-mp4 out.mp4
        """,
    )

    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Input video file",
    )

    parser.add_argument(
        "--web",
        action="store_true",
        help="Start web GUI server",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=9999,
        help="Port for web GUI server (default: 9999, used with --web)",
    )

    parser.add_argument(
        "--preset",
        type=str,
        choices=list(PRESETS.keys()),
        default=None,
        metavar="NAME",
        help=f"Apply a preset ({', '.join(PRESETS.keys())})",
    )

    parser.add_argument(
        "--width",
        type=int,
        default=None,
        help="ASCII output width in characters (default: 160, or from preset)",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=None,
        help="Frames per second to extract/play (default: 12, or from preset)",
    )

    parser.add_argument(
        "--color",
        action="store_true",
        default=None,
        help="Enable ANSI color output",
    )

    parser.add_argument(
        "--crt",
        action="store_true",
        help="Shorthand for --preset crt",
    )

    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop playback forever",
    )

    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Playback speed multiplier (default: 1.0)",
    )

    parser.add_argument(
        "--invert",
        action="store_true",
        default=None,
        help="Invert brightness (dark mode friendly)",
    )

    parser.add_argument(
        "--edge",
        action="store_true",
        default=None,
        help="Edge detection for artistic effect",
    )

    parser.add_argument(
        "--edge-threshold",
        type=float,
        default=0.15,
        metavar="N",
        help="Edge detection threshold (0.0-1.0, default: 0.15, higher=fewer edges)",
    )

    parser.add_argument(
        "--charset",
        type=str,
        default=None,
        metavar="NAME",
        help=f"Character set: {', '.join(CHARSETS.keys())}, or custom string (default: classic). PETSCII gives Commodore 64 retro look.",
    )

    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress bar during playback",
    )

    parser.add_argument(
        "--export",
        type=Path,
        metavar="FILE",
        help="Package as standalone playable script",
    )

    parser.add_argument(
        "--export-mp4",
        type=Path,
        metavar="FILE",
        help="Export ASCII frames as MP4 video file (H.265/HEVC encoding)",
    )

    parser.add_argument(
        "--export-prores422",
        type=Path,
        metavar="FILE",
        help="Export ASCII frames as video file using ProRes 422 HQ codec",
    )

    parser.add_argument(
        "--subtitle",
        action="store_true",
        help="Auto-generate subtitles from audio (requires whisper-cli from whisper-cpp)",
    )

    parser.add_argument(
        "--font",
        type=str,
        default=None,
        metavar="NAME_OR_PATH",
        help="Font for MP4/ProRes export (e.g. PetMe128, /path/to/font.ttf). "
             "PetMe variants: PetMe, PetMe64, PetMe128, PetMe2X, PetMe2Y, PetMe642Y, PetMe1282Y",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Delete temp files after playback",
    )

    parser.add_argument(
        "--aspect-ratio",
        type=float,
        default=1.2,
        help="Terminal character aspect ratio correction (default: 1.2, lower=shorter output)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Configure logging based on verbose flag
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(levelname)s: %(message)s",
        )
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("PIL.PngImagePlugin").setLevel(logging.WARNING)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
        )

    # --crt is shorthand for --preset crt
    if args.crt and args.preset is None:
        args.preset = "crt"

    # Apply preset defaults, then let explicit CLI flags override
    preset = PRESETS.get(args.preset, {}) if args.preset else {}

    if args.width is None:
        args.width = preset.get("width", 160)
    if args.fps is None:
        args.fps = preset.get("fps", 12)
    if args.color is None:
        args.color = preset.get("color", False)
    if args.invert is None:
        args.invert = preset.get("invert", False)
    if args.edge is None:
        args.edge = preset.get("edge", False)
    if args.charset is None:
        args.charset = preset.get("charset", "classic")

    # Derive color_scheme and crt_filter from the preset
    args.color_scheme = preset.get("color_scheme", None)
    args.crt_filter = preset.get("crt_filter", False)

    # Validate arguments (skip if --web is used)
    if not args.web:
        if not args.input:
            parser.error("input file is required (or use --web to start web GUI)")
        if not args.input.exists():
            parser.error(f"Input file not found: {args.input}")

    if args.width < 20:
        parser.error("--width must be at least 20")

    if args.fps < 1:
        parser.error("--fps must be at least 1")

    if args.speed <= 0:
        parser.error("--speed must be positive")

    return args


def main():
    """Main entry point."""
    args = parse_args()

    # Handle --web flag
    if args.web:
        try:
            import uvicorn
            from video2ascii.web.app import app
            import webbrowser
            import threading

            port = args.port
            url = f"http://localhost:{port}"

            def open_browser():
                import time
                time.sleep(1.5)
                webbrowser.open(url)

            threading.Thread(target=open_browser, daemon=True).start()

            print(f"Starting video2ascii web GUI...")
            print(f"Open your browser to: {url}")
            print("Press Ctrl+C to stop the server")

            uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
            return
        except ImportError:
            print("Error: Web dependencies not installed.", file=sys.stderr)
            print("Install with: uv pip install -e '.[web]' or pip install -e '.[web]'", file=sys.stderr)
            sys.exit(1)


    logger.info(f"Input file: {args.input}")
    logger.debug(f"Arguments: width={args.width}, fps={args.fps}, color={args.color}, "
                 f"charset={args.charset}, preset={args.preset}, edge={args.edge}, invert={args.invert}")

    # Check dependencies
    logger.debug("Checking ffmpeg availability...")
    check_ffmpeg()

    # Create working directory
    base_name = args.input.stem
    work_dir = Path(tempfile.mkdtemp(prefix=f"ascii_{base_name}_"))
    logger.info(f"Working dir: {work_dir}")

    try:
        logger.info(f"Extracting frames @ {args.fps} fps…")

        # Extract frames
        frame_paths = extract_frames(
            args.input,
            args.fps,
            args.width,
            work_dir,
            crt_filter=args.crt_filter,
        )

        logger.info(f"Extracted {len(frame_paths)} frames")
        logger.debug(f"Frame paths: {[str(p) for p in frame_paths[:3]]}..." if len(frame_paths) > 3 else f"Frame paths: {[str(p) for p in frame_paths]}")

        logger.info(f"Converting {len(frame_paths)} frames to ASCII (width={args.width}, charset={args.charset})…")

        # Convert to ASCII
        frames = convert_all(
            frame_paths,
            args.width,
            color=args.color,
            invert=args.invert,
            edge=args.edge,
            aspect_ratio=args.aspect_ratio,
            edge_threshold=args.edge_threshold,
            charset=args.charset,
        )

        logger.info(f"Converted {len(frames)} frames to ASCII")

        # Generate subtitles if requested
        subtitle_segments = None
        subtitle_srt_path = None
        if args.subtitle:
            from video2ascii.subtitle import generate_srt, parse_srt

            logger.info("Generating subtitles from audio...")
            subtitle_srt_path = generate_srt(args.input, work_dir)
            if subtitle_srt_path:
                subtitle_segments = parse_srt(subtitle_srt_path)
                logger.info(f"Generated {len(subtitle_segments)} subtitle segments")
            else:
                logger.warning("Subtitle generation failed, continuing without subtitles")

        # Export modes
        if args.export:
            if args.font:
                logger.debug("--font ignored for .sh export (only applies to MP4/ProRes)")
            logger.info(f"Packaging {len(frames)} frames into: {args.export}")
            export(frames, args.export, args.fps, args.crt_filter)
            return

        if args.export_mp4:
            target_mp4_width = min(1920, max(1280, args.width * 16))
            logger.debug(f"MP4 target width: {target_mp4_width} (scaled from ASCII width {args.width})")
            export_mp4(
                frames,
                args.export_mp4,
                args.fps,
                color=args.color,
                color_scheme=args.color_scheme,
                work_dir=work_dir,
                charset=args.charset,
                target_width=target_mp4_width,
                codec="h265",
                subtitle_path=subtitle_srt_path,
                font_override=args.font,
            )
            return

        if args.export_prores422:
            target_mp4_width = min(1920, max(1280, args.width * 16))
            logger.debug(f"ProRes 422 target width: {target_mp4_width} (scaled from ASCII width {args.width})")
            export_mp4(
                frames,
                args.export_prores422,
                args.fps,
                color=args.color,
                color_scheme=args.color_scheme,
                work_dir=work_dir,
                charset=args.charset,
                target_width=target_mp4_width,
                codec="prores422",
                subtitle_path=subtitle_srt_path,
                font_override=args.font,
            )
            return

        # Playback mode
        logger.info("Playing in terminal… (Ctrl-C to stop)")
        if args.loop:
            logger.info("(Looping enabled)")
        if args.preset:
            logger.info(f"(Preset: {args.preset})")
        if args.charset.lower() == "petscii":
            logger.info("(PETSCII mode: For best results, use KreativeKorp Pet Me fonts)")
            logger.info("  Variants: PetMe, PetMe64, PetMe128, PetMe2X, PetMe2Y, PetMe642Y, PetMe1282Y")
            logger.info("  Install: https://www.kreativekorp.com/software/fonts/c64/")

        play(
            frames,
            args.fps,
            speed=args.speed,
            color_scheme=args.color_scheme,
            loop=args.loop,
            progress=args.progress,
            subtitle_segments=subtitle_segments,
        )

    finally:
        # Cleanup
        if args.no_cache:
            logger.debug(f"Cleaning up work directory: {work_dir}")
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            logger.info(f"Cached output kept at: {work_dir}")
            logger.info(f"ASCII frames: {work_dir / 'frames'}")


if __name__ == "__main__":
    main()
