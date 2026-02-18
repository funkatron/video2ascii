# Examples

This directory contains example exported ASCII movies created with `video2ascii --export` and `video2ascii --export-mp4`.

## Available Examples

### Shell Scripts (Terminal Playback)

- `not-ai.sh` - Default classic charset
- `not-ai-classic.sh` - Classic character set
- `not-ai-petscii.sh` - PETSCII character set (Commodore 64 style)
- `not-ai-blocks.sh` - Unicode block characters
- `not-ai-dense.sh` - Dense character set (high detail)
- `not-ai-braille.sh` - Braille characters (high resolution)

### MP4 Videos (Color Rendering)

- `video2ascii-classic-color.mp4` - Classic charset with color
- `video2ascii-blocks-color.mp4` - Unicode blocks with color
- `video2ascii-braille-color.mp4` - Braille with enhanced brightness and bold effect
- `video2ascii-dense-color.mp4` - Dense charset with color
- `video2ascii-simple-color.mp4` - Simple charset with color
- `video2ascii-petscii-color.mp4` - PETSCII charset with color

### Subtitle Examples (Sintel Trailer)

Shell scripts with auto-generated subtitles, one per charset:

- `sintel-subtitle-classic.sh` - Classic charset
- `sintel-subtitle-blocks.sh` - Unicode blocks
- `sintel-subtitle-braille.sh` - Braille characters
- `sintel-subtitle-dense.sh` - Dense charset
- `sintel-subtitle-simple.sh` - Simple charset
- `sintel-subtitle-petscii.sh` - PETSCII charset

Subtitles are auto-generated from the audio via whisper-cli (whisper.cpp) with Voice Activity Detection (VAD) for accurate timing. The Sintel trailer dialogue:

> "What brings you to the land of the gatekeepers?"
> "I'm searching for someone."
> "A dangerous quest for our lone hunter."
> "I've been alone for as long as I can remember."

## Running Examples

All exported scripts are self-contained and require only bash:

```bash
# Play an example
./examples/not-ai.sh

# With options
./examples/not-ai.sh --loop --crt
./examples/not-ai.sh --speed 1.5 --progress

# Try different character sets
./examples/not-ai-petscii.sh --crt
./examples/not-ai-blocks.sh --loop

# Play subtitle demos
./examples/sintel-subtitle-classic.sh
./examples/sintel-subtitle-petscii.sh --loop --progress
```

## Creating Your Own

Export your own ASCII movies:

```bash
# Shell script (terminal playback)
video2ascii input.mp4 --export examples/my-movie.sh
video2ascii input.mp4 --charset petscii --crt --export examples/retro-movie.sh

# With subtitles
video2ascii input.mp4 --subtitle --export examples/subtitled-movie.sh

# MP4 video (color rendering)
video2ascii input.mp4 --color --charset classic --export-mp4 examples/my-movie.mp4
video2ascii input.mp4 --color --charset braille --export-mp4 examples/my-braille-movie.mp4

# MP4 with subtitles burned in
video2ascii input.mp4 --color --subtitle --export-mp4 examples/subtitled.mp4

# MP4 with specific font (useful for PETSCII)
video2ascii input.mp4 --charset petscii --font PetMe128 --export-mp4 examples/petscii.mp4
```

## Web GUI

You can also create and preview ASCII art using the browser-based web GUI:

```bash
# Install web dependencies
uv pip install -e ".[web]"

# Launch the web GUI
video2ascii --web
```

The web GUI supports drag-and-drop upload, presets, live playback, subtitle generation, font selection for PETSCII, and export to .sh or .mp4.
