# video2ascii

Convert any video to ASCII art and play it in your terminal.

## Demo

```bash
# Classic ASCII
video2ascii your-video.mp4

# Retro CRT mode - 80 columns, green phosphor color
video2ascii your-video.mp4 --crt

# Edge detection (sketch-like effect)
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
- Pillow (installed automatically)
- **[uv](https://github.com/astral-sh/uv)** (recommended) or pip/pipx

## Installation

### Option 1: Install with uv (recommended)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package
uv pip install .

# Or install in editable mode with dev dependencies
uv pip install -e ".[dev]"
```

### Option 2: Install with pip/pipx

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Install with pip
pip install .

# Or install with pipx (recommended for CLI tools)
pipx install .
```

### Option 3: Run directly (no install)

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Run directly with uv
uv run python -m video2ascii input.mp4

# Or run directly with Python
python3 -m video2ascii input.mp4
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

# Edge detection (sketch-like effect)
video2ascii input.mp4 --edge --invert --color

# Combine CRT with loop and progress
video2ascii input.mp4 --crt --loop --progress

# Commodore 64 PETSCII style
video2ascii input.mp4 --charset petscii --crt

# Export as standalone playable file (no dependencies!)
video2ascii input.mp4 --export movie.sh
./movie.sh --loop --crt

# Export as MP4 video file (H.265/HEVC encoding)
video2ascii input.mp4 --charset petscii --crt --export-mp4 ascii-video.mp4

# Export as ProRes 422 HQ (larger file size)
video2ascii input.mp4 --color --charset braille --export-prores422 ascii-prores.mov
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--width N` | ASCII output width in characters | 160 |
| `--fps N` | Frames per second to extract/play | 12 |
| `--color` | Enable ANSI color output | off |
| `--crt` | Retro CRT mode: 80 columns, green phosphor color | off |
| `--loop` | Loop playback forever | off |
| `--speed N` | Playback speed multiplier (0.5, 1.0, 2.0, etc.) | 1.0 |
| `--invert` | Invert brightness (dark mode friendly) | off |
| `--edge` | Edge detection for sketch-like effect | off |
| `--edge-threshold N` | Edge detection threshold (0.0-1.0) | 0.15 |
| `--charset NAME` | Character set: classic, blocks, braille, dense, simple, petscii | classic |
| `--aspect-ratio N` | Terminal character aspect ratio correction | 1.2 |
| `--progress` | Show progress bar during playback | off |
| `--export FILE` | Package as standalone playable script | - |
| `--export-mp4 FILE` | Export ASCII frames as MP4 video file (H.265/HEVC encoding) | - |
| `--export-prores422 FILE` | Export ASCII frames as video file using ProRes 422 HQ codec | - |
| `--no-cache` | Delete temp files after playback | keep |
| `-h, --help` | Show help message | - |

## Modes

### CRT Mode (`--crt`)

Applies retro terminal settings:
- Fixed 80-column width (like classic terminals)
- Green phosphor color tint (#33FF33) - applies green color to all text
- Inverted colors (light on dark, like real CRTs)
- Enhanced contrast via unsharp filter during frame extraction

Simulates 1980s computer terminal appearance.

### Edge Detection (`--edge`)

Uses Sobel-based edge detection with Gaussian blur and thresholding to extract clean outlines from the video. Creates a sketch-like effect by highlighting edges and suppressing other details. Combine with `--invert` for improved contrast. Use `--edge-threshold` to control sensitivity (lower = more edges).

### Character Sets (`--charset`)

Character sets available:

- **`classic`** (default): Balanced traditional ASCII art (`" .:-=+*#%@"`)
- **`blocks`**: Bold Unicode block characters (`" ░▒▓█"`)
- **`braille`**: Braille characters (Unicode U+2800-U+28FF)
- **`dense`**: Many characters for fine gradients and detail
- **`simple`**: Minimal character set (`" .oO0"`)
- **`petscii`**: True Commodore 64 PETSCII graphics characters using Unicode 13.0+ Symbols for Legacy Computing block
  - For Commodore 64 appearance, use [KreativeKorp Pet Me 64 fonts](https://www.kreativekorp.com/software/fonts/c64/) in your terminal. These fonts render the PETSCII Unicode characters.

You can also provide a custom character string ordered from darkest to lightest.

### Export Modes

#### Standalone Script (`--export FILE`)

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

Use cases:
- Sharing ASCII art animations
- Terminal screensavers
- Embedding in dotfiles or scripts
- Email attachments

#### MP4 Video (`--export-mp4 FILE`)

Renders ASCII frames as images and creates an MP4 video file:
- Renders ASCII art using system monospace fonts (automatically finds PetME64, Iosevka, Menlo, Courier, or DejaVu)
- Preserves color information (if `--color` was used)
- Applies CRT green tint (if `--crt` was used)
- Creates MP4 file playable in any video player
- When using `--charset petscii`, automatically prefers PetME64 font for Commodore 64 rendering

**Codec Options:**

- `--export-mp4 FILE`: Uses H.265/HEVC encoding (default, better compression, smaller file size)
- `--export-prores422 FILE`: Uses ProRes 422 HQ encoding (larger file size, suitable for video editing)

**Font Support:**
The MP4 exporter automatically searches for fonts in common locations:
- **PetME64** (KreativeKorp): `~/Library/Fonts/`, `/Library/Fonts/` (macOS) or `~/.fonts/`, `/usr/share/fonts/` (Linux)
- **Iosevka**: Same locations as PetME64
- **VT323**: Retro terminal font
- **IBM Plex Mono**: Monospace font
- **System fonts**: Menlo, Courier, DejaVu Sans Mono, Liberation Mono

```bash
# Export as MP4 (H.265/HEVC - default)
video2ascii video.mp4 --charset petscii --crt --export-mp4 output.mp4

# Export as ProRes 422 HQ
video2ascii video.mp4 --color --charset braille --export-prores422 output-prores.mov

# With color
video2ascii video.mp4 --color --export-mp4 colorful-ascii.mp4

# PETSCII with PetME64 font (if installed)
video2ascii video.mp4 --charset petscii --export-mp4 petscii-video.mp4
```

Use cases:
- Sharing on social media
- Embedding in websites
- Creating demos or presentations
- Archiving ASCII art animations

## How It Works

1. **Frame Extraction**: Uses `ffmpeg` to extract frames at the specified FPS and scale them to the target width
2. **ASCII Conversion**: Uses Pillow to convert each frame to ASCII art (parallelized across CPU cores). Maps pixel brightness to character density ramp: `" .:-=+*#%@"`
3. **Playback**: Displays frames sequentially in the terminal using ANSI escape sequences for smooth animation

## Tips

- **CRT Mode**: Works best in a terminal with a dark background. Retro fonts like "VT323" or "IBM Plex Mono" can enhance the appearance.
- **PETSCII Mode**: Install and use the [KreativeKorp Pet Me 64 fonts](https://www.kreativekorp.com/software/fonts/c64/) in your terminal. These fonts render the PETSCII Unicode characters (Unicode 13.0+ Symbols for Legacy Computing block).
- **Width**: For CRT mode, 80 is classic. For modern displays, try 120-200 depending on your terminal size.
- **FPS**: Higher FPS = smoother playback but more processing. 10-15 FPS works well for most content.
- **Speed**: Use `--speed 0.5` for slow-mo, `--speed 2` for double-speed.
- **Edge + Color**: Combining edge detection with color preserves color information along detected edges.
- **Aspect Ratio**: Terminal characters are roughly 2:1 height:width, so the tool automatically adjusts frame height for proper proportions.

## Development

This project uses `uv` for package management and development workflows.

```bash
# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=video2ascii

# Run the tool directly
uv run python -m video2ascii input.mp4
```

The project also works with standard pip/pipx workflows if you prefer.

## Performance

The tool parallelizes frame conversion across all available CPU cores using Python's `multiprocessing`, making the processing phase significantly faster on multi-core systems.

Cached frames are stored in `/tmp/ascii_FILENAME.XXXXXX/` by default. Use `--no-cache` to clean up automatically, or manually delete the temp directory.

## Controls

- **Ctrl+C**: Stop playback and exit

## License

MIT
