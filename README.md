# video2ascii

Convert any video to ASCII art and play it in your terminal.

## Demo

```
./video2ascii your-video.mp4
```

The script extracts frames from the video, converts each to ASCII art, and plays them back in sequence in your terminal.

## Requirements

**macOS:**
```bash
brew install ffmpeg jp2a
```

**Linux (Debian/Ubuntu):**
```bash
apt install ffmpeg jp2a
```

**Other Linux:**
```bash
# Use your package manager to install ffmpeg and jp2a
```

## Installation

```bash
# Clone or download this repository
git clone https://github.com/YOUR_USERNAME/video2ascii.git
cd video2ascii

# Make the script executable
chmod +x video2ascii

# Optionally, add to your PATH
cp video2ascii /usr/local/bin/
```

## Usage

```bash
# Basic usage (defaults: 160 width, 12 fps)
./video2ascii input.mp4

# Custom width and framerate
./video2ascii input.mp4 --width 120 --fps 15

# Enable color output (requires terminal with ANSI color support)
./video2ascii input.mp4 --color

# Don't cache frames after playback
./video2ascii input.mp4 --no-cache

# Combine options
./video2ascii input.mp4 --width 100 --fps 10 --color
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--width N` | ASCII output width in characters | 160 |
| `--fps N` | Frames per second to extract/play | 12 |
| `--color` | Enable ANSI color output | off |
| `--no-cache` | Delete temp files after playback | keep |
| `-h, --help` | Show help message | - |

## How It Works

1. **Frame Extraction**: Uses `ffmpeg` to extract frames at the specified FPS and scale them to the target width
2. **ASCII Conversion**: Uses `jp2a` to convert each frame to ASCII art (parallelized across CPU cores)
3. **Playback**: Displays frames sequentially in the terminal using ANSI escape sequences for smooth animation

## Tips

- **Width**: Larger widths show more detail but require a wider terminal. Start with your terminal width minus some margin.
- **FPS**: Higher FPS = smoother playback but more processing. 10-15 FPS works well for most content.
- **Font**: Use a monospace font with consistent character dimensions for best results.
- **Color**: Works best with videos that have distinct colors. Requires a terminal that supports ANSI colors.

## Performance

The script parallelizes frame conversion across all available CPU cores, making the processing phase significantly faster on multi-core systems.

Cached frames are stored in `/tmp/ascii_FILENAME.XXXXXX/` by default. Use `--no-cache` to clean up automatically, or manually delete the temp directory.

## Controls

- **Ctrl+C**: Stop playback and exit

## License

MIT
