"""Convert ANSI color codes to HTML for browser rendering."""

import re
from typing import Optional


def ansi_to_html(ascii_text: str, crt: bool = False) -> str:
    """
    Convert ANSI color codes to HTML spans for browser rendering.
    
    Args:
        ascii_text: ASCII art string with ANSI color codes (from image_to_ascii with color=True)
        crt: Apply CRT green phosphor tint to all text
        
    Returns:
        HTML string with <span> tags for colored characters
    """
    if not ascii_text:
        return ""
    
    # Check if there are any ANSI codes at all
    if "\033" not in ascii_text:
        # Plain text - just escape HTML and apply CRT if needed
        escaped = _escape_html(ascii_text)
        if crt:
            return f'<span style="color: rgb(51, 255, 51)">{escaped}</span>'
        return escaped
    
    # ANSI color code pattern: \033[38;2;R;G;Bm or \033[0m (reset)
    # Also handle CRT codes: \033[38;2;51;255;51m (green) and \033[48;2;5;5;5m (dark bg)
    ansi_pattern = re.compile(
        r'\033\[(?:38;2;(\d+);(\d+);(\d+)|48;2;(\d+);(\d+);(\d+)|0)m'
    )
    
    result = []
    i = 0
    current_color: Optional[tuple[int, int, int]] = None
    current_bg: Optional[tuple[int, int, int]] = None
    
    for match in ansi_pattern.finditer(ascii_text):
        # Text before code
        text_before = ascii_text[i:match.start()]
        if text_before:
            result.append(_wrap_text(text_before, current_color, current_bg, crt))
        
        # Parse ANSI code
        r, g, b = match.groups()[:3]
        bg_r, bg_g, bg_b = match.groups()[3:]
        
        if r is not None and g is not None and b is not None:
            current_color = (int(r), int(g), int(b))
        elif bg_r is not None and bg_g is not None and bg_b is not None:
            current_bg = (int(bg_r), int(bg_g), int(bg_b))
        else:
            # Reset (0m)
            current_color = None
            current_bg = None
        
        i = match.end()
    
    # Add remaining text
    text_after = ascii_text[i:]
    if text_after:
        result.append(_wrap_text(text_after, current_color, current_bg, crt))
    
    # If no ANSI codes were found but we have text, return it wrapped
    if not result and ascii_text:
        escaped = _escape_html(ascii_text)
        if crt:
            return f'<span style="color: rgb(51, 255, 51)">{escaped}</span>'
        return escaped
    
    return "".join(result)


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _wrap_text(
    text: str,
    color: Optional[tuple[int, int, int]],
    bg: Optional[tuple[int, int, int]],
    crt: bool,
) -> str:
    """Wrap text in span with color styling."""
    if not text:
        return ""

    escaped = _escape_html(text)

    # Apply CRT green tint if requested
    if crt and color is None:
        color = (51, 255, 51)  # CRT green

    styles = []
    if color:
        if crt:
            # Blend with CRT green: mix original color with green phosphor
            r, g, b = color
            # Green phosphor effect: boost green channel
            crt_r = int((r * 0.2) + (51 * 0.8))
            crt_g = int((g * 0.2) + (255 * 0.8))
            crt_b = int((b * 0.2) + (51 * 0.8))
            styles.append(f"color: rgb({crt_r}, {crt_g}, {crt_b})")
        else:
            styles.append(f"color: rgb({color[0]}, {color[1]}, {color[2]})")

    if bg:
        styles.append(f"background-color: rgb({bg[0]}, {bg[1]}, {bg[2]})")

    if styles:
        style_attr = "; ".join(styles)
        return f'<span style="{style_attr}">{escaped}</span>'
    else:
        return escaped


def frames_to_html(frames: list[str], crt: bool = False) -> list[str]:
    """
    Convert a list of ANSI-formatted ASCII frames to HTML.

    Args:
        frames: List of ASCII art strings (may contain ANSI codes)
        crt: Apply CRT green phosphor tint

    Returns:
        List of HTML strings
    """
    return [ansi_to_html(frame, crt=crt) for frame in frames]
