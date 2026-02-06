"""Export ASCII frames as standalone bash script."""

import base64
import gzip
from pathlib import Path


def export(
    frames: list[str],
    output_path: Path,
    fps: int,
    crt: bool,
) -> None:
    """
    Export frames as standalone bash script.
    
    Args:
        frames: List of ASCII art frame strings
        output_path: Path to output bash script
        fps: Original frames per second
        crt: Original CRT mode setting
    """
    # Read player template
    template_path = Path(__file__).parent / "player_template.sh"
    with open(template_path, "r") as f:
        template = f.read()
    
    # Replace metadata placeholders
    template = template.replace("ORIG_FPS=12", f"ORIG_FPS={fps}")
    template = template.replace("ORIG_CRT=0", f"ORIG_CRT={1 if crt else 0}")
    template = template.replace("TOTAL_FRAMES=0", f"TOTAL_FRAMES={len(frames)}")
    
    # Write header
    with open(output_path, "w") as f:
        f.write(template)
        f.write("\n")
        
        # Compress and encode frames
        for frame in frames:
            f.write("---FRAME---\n")
            # Compress frame
            compressed = gzip.compress(frame.encode("utf-8"))
            # Base64 encode
            encoded = base64.b64encode(compressed).decode("ascii")
            # Write as single line (bash can handle long lines)
            f.write(encoded)
            f.write("\n")
    
    # Make executable
    output_path.chmod(0o755)
    
    # Calculate file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Created: {output_path} ({size_mb:.2f}MB, {len(frames)} frames @ {fps} fps)")
    print()
    print("Play with:")
    print(f"  ./{output_path.name}")
    print(f"  ./{output_path.name} --loop --crt")
    print(f"  ./{output_path.name} --speed 2 --progress")
