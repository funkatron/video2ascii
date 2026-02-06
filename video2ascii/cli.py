"""Command-line interface."""

import argparse
import sys
import tempfile
from pathlib import Path

from video2ascii import __version__
from video2ascii.converter import check_ffmpeg, extract_frames, convert_all, CHARSETS
from video2ascii.exporter import export
from video2ascii.player import play


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
  %(prog)s input.mp4 --crt
  %(prog)s input.mp4 --edge --invert
  %(prog)s input.mp4 --loop --speed 1.5 --progress
  %(prog)s input.mp4 --export movie.sh
        """,
    )
    
    parser.add_argument(
        "input",
        type=Path,
        help="Input video file",
    )
    
    parser.add_argument(
        "--width",
        type=int,
        default=160,
        help="ASCII output width in characters (default: 160)",
    )
    
    parser.add_argument(
        "--fps",
        type=int,
        default=12,
        help="Frames per second to extract/play (default: 12)",
    )
    
    parser.add_argument(
        "--color",
        action="store_true",
        help="Enable ANSI color output",
    )
    
    parser.add_argument(
        "--crt",
        action="store_true",
        help="Retro CRT mode: 80 columns, green phosphor",
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
        help="Invert brightness (dark mode friendly)",
    )
    
    parser.add_argument(
        "--edge",
        action="store_true",
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
        default="classic",
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
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.input.exists():
        parser.error(f"Input file not found: {args.input}")
    
    if args.width < 20:
        parser.error("--width must be at least 20")
    
    if args.fps < 1:
        parser.error("--fps must be at least 1")
    
    if args.speed <= 0:
        parser.error("--speed must be positive")
    
    # CRT mode overrides width
    if args.crt:
        args.width = 80
        args.color = True
    
    return args


def main():
    """Main entry point."""
    args = parse_args()
    
    # Check dependencies
    check_ffmpeg()
    
    # Create working directory
    base_name = args.input.stem
    work_dir = Path(tempfile.mkdtemp(prefix=f"ascii_{base_name}_"))
    
    try:
        print(f"Working dir: {work_dir}")
        print(f"Extracting frames @ {args.fps} fps…")
        
        # Extract frames
        frame_paths = extract_frames(
            args.input,
            args.fps,
            args.width,
            work_dir,
            crt=args.crt,
        )
        
        print(f"Converting {len(frame_paths)} frames to ASCII (width={args.width})…")
        
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
        
        # Export mode
        if args.export:
            print(f"Packaging {len(frames)} frames into: {args.export}")
            export(frames, args.export, args.fps, args.crt)
            return
        
        # Playback mode
        print("Playing in terminal… (Ctrl-C to stop)")
        if args.loop:
            print("(Looping enabled)")
        if args.crt:
            print("(CRT mode: 80 columns, green phosphor)")
        
        play(
            frames,
            args.fps,
            speed=args.speed,
            crt=args.crt,
            loop=args.loop,
            progress=args.progress,
        )
    
    finally:
        # Cleanup
        if args.no_cache:
            import shutil
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            print()
            print(f"Cached output kept at: {work_dir}")
            print(f"ASCII frames: {work_dir / 'frames'}")


if __name__ == "__main__":
    main()
