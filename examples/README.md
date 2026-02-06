# Examples

This directory contains example exported ASCII movies created with `video2ascii --export`.

## Available Examples

- `not-ai.sh` - Default classic charset
- `not-ai-classic.sh` - Classic character set
- `not-ai-petscii.sh` - PETSCII character set (Commodore 64 style)
- `not-ai-blocks.sh` - Unicode block characters
- `not-ai-dense.sh` - Dense character set (high detail)
- `not-ai-braille.sh` - Braille characters (high resolution)

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
video2ascii input.mp4 --export examples/my-movie.sh
video2ascii input.mp4 --charset petscii --crt --export examples/retro-movie.sh
```
