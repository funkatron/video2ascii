# video2ascii

Convert any video to ASCII art and play it in your terminal.

## Demo

```bash
# Classic ASCII
video2ascii your-video.mp4

# Retro CRT mode - 80 columns, green phosphor glow
video2ascii your-video.mp4 --crt

# Artistic edge detection
video2ascii your-video.mp4 --edge --invert
```

The tool extracts frames from the video, converts each to ASCII art using Pillow, and plays them back in sequence in your terminal.

## Requirements

**System dependencies:**
- **ffmpeg** (for video frame extraction)
  - macOS: `brew install ffmpeg`
  - Linux: `apt install ffmpeg` (or equivalent)

**Python dependencies:**
- Python 3.10+
- Pillow (installed automatically via pip)

## Installation

### Option 1: Install from source

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Install with pip
pip install .

# Or install with pipx (recommended for CLI tools)
pipx install .
```

### Option 2: Run directly (no install)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Run directly
python3 -m video2ascii input.mp4

# Or make it executable
chmod +x video2ascii/cli.py
./video2ascii/cli.py input.mp4
```

## Usage

```bash
# Basic usage (defaults: 160 width, 12 fps)
video2ascii input.mp4

# Custom width and framerate
video2ascii input.mp4 --width 120 --fps 15

# Enable color output
video2ascii input.mp4 --color

# Retro CRT mode (80 columns, green phosphor)
video2ascii input.mp4 --crt

# Loop forever at 1.5x speed with progress bar
video2ascii input.mp4 --loop --speed 1.5 --progress

# Artistic edge detection (great for music videos)
video2ascii input.mp4 --edge --invert --color

# Combine for ultimate retro experience
video2ascii input.mp4 --crt --loop --progress

# Commodore 64 PETSCII style
video2ascii input.mp4 --charset petscii --crt

# Export as standalone playable file (no dependencies!)
video2ascii input.mp4 --export movie.sh
./movie.sh --loop --crt
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--width N` | ASCII output width in characters | 160 |
| `--fps N` | Frames per second to extract/play | 12 |
| `--color` | Enable ANSI color output | off |
| `--crt` | Retro CRT mode: 80 columns, green phosphor | off |
| `--loop` | Loop playback forever | off |
| `--speed N` | Playback speed multiplier (0.5, 1.0, 2.0, etc.) | 1.0 |
| `--invert` | Invert brightness (dark mode friendly) | off |
| `--edge` | Edge detection for artistic effect | off |
| `--edge-threshold N` | Edge detection threshold (0.0-1.0) | 0.15 |
| `--charset NAME` | Character set: classic, blocks, braille, dense, simple, petscii | classic |
| `-- N` | Terminal character aspect ratio correction | 1.2 |
| `--progress` | Show progress bar during playback | off |
| `--export FILE` | Package as standalone playable script | - |
| `--no-cache` | Delete temp files after playback | keep |
| `-h, --help` | Show help message | - |

## Modes

### CRT Mode (`--crt`)

Activates a retro terminal aesthetic:
- Fixed 80-column width (like classic terminals)
- Green phosphor color (#33FF33)
- Inverted colors (light on dark, like real CRTs)
- Enhanced contrast

Perfect for that 1980s computer terminal vibe.

### Edge Detection (`--edge`)

Uses improved Sobel-based edge detection with Gaussian blur and thresholding to extract clean outlines from the video. Creates an artistic, sketch-like effect. Combine with `--invert` for best results. Use `--edge-threshold` to control sensitivity (lower = more edges).

### Character Sets (`--charset`)

Choose from different character sets for different visual styles:

- **`classic`** (default): Balanced traditional ASCII art (`" .:-=+*#%@"`)
- **`blocks`**: Bold Unicode block characters (`" ░▒▓█"`)
- **`braille`**: High-resolution braille characters for maximum detail
- **`dense`**: Many characters for fine gradients and detail
- **`simple`**: Minimal clean look (`" .oO0"`)
- **`petscii`**: True Commodore 64 PETSCII graphics characters using Unicode 13.0+ Symbols for Legacy Computing block
  - **Tip**: For authentic Commodore 64 look, use [KreativeKorp Pet Me 64 fonts](https://www.kreativekorp.com/software/fonts/c64/) in your terminal. These fonts properly render the PETSCII Unicode characters.

You can also provide a custom character string ordered from darkest to lightest.

### Export Mode (`--export FILE`)

Packages all ASCII frames into a **single, self-playing bash script**. The exported file:
- Has **zero dependencies** (just bash)
- Contains all frames embedded inline (compressed with gzip+base64)
- Supports `--loop`, `--speed`, `--crt`, `--progress` at playback
- Is portable and shareable

```bash
# Create a standalone ASCII movie
video2ascii video.mp4 --crt --export retro_movie.sh

# Share with friends - they just need bash!
./retro_movie.sh
./retro_movie.sh --loop --speed 1.5
```

Great for:
- Sharing ASCII art animations
- Terminal screensavers
- Embedding in dotfiles or scripts
- Fun email attachments

## How It Works

1. **Frame Extraction**: Uses `ffmpeg` to extract frames at the specified FPS and scale them to the target width
2. **ASCII Conversion**: Uses Pillow to convert each frame to ASCII art (parallelized across CPU cores). Maps pixel brightness to character density ramp: `" .:-=+*#%@"`
3. **Playback**: Displays frames sequentially in the terminal using ANSI escape sequences for smooth animation

## Tips

- **CRT Mode**: Works best in a terminal with a dark background. Try a retro font like "VT323" or "IBM Plex Mono" for extra authenticity.
- **PETSCII Mode**: For the most authentic Commodore 64 experience, install and use the [KreativeKorp Pet Me 64 fonts](https://www.kreativekorp.com/software/fonts/c64/) in your terminal. These fonts properly render the official PETSCII Unicode characters (Unicode 13.0+ Symbols for Legacy Computing block).
- **Width**: For CRT mode, 80 is classic. For modern displays, try 120-200 depending on your terminal size.
- **FPS**: Higher FPS = smoother playback but more processing. 10-15 FPS works well for most content.
- **Speed**: Use `--speed 0.5` for slow-mo, `--speed 2` for double-speed.
- **Edge + Color**: Combining edge detection with color can create interesting neon-like effects.
- **Aspect Ratio**: Terminal characters are roughly 2:1 height:width, so the tool automatically adjusts frame height for proper proportions.

## Performance

The tool parallelizes frame conversion across all available CPU cores using Python's `multiprocessing`, making the processing phase significantly faster on multi-core systems.

Cached frames are stored in `/tmp/ascii_FILENAME.XXXXXX/` by default. Use `--no-cache` to clean up automatically, or manually delete the temp directory.

## Controls

- **Ctrl+C**: Stop playback and exit

## License

MIT
