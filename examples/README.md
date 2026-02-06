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
```

## Creating Your Own

Export your own ASCII movies:

```bash
# Shell script (terminal playback)
video2ascii input.mp4 --export examples/my-movie.sh
video2ascii input.mp4 --charset petscii --crt --export examples/retro-movie.sh

# MP4 video (color rendering)
video2ascii input.mp4 --color --charset classic --export-mp4 examples/my-movie.mp4
video2ascii input.mp4 --color --charset braille --export-mp4 examples/my-braille-movie.mp4
```
