"""Convert ANSI color codes to HTML for browser rendering."""

import re
from typing import Optional

from video2ascii.presets import ColorScheme


def ansi_to_html(ascii_text: str, color_scheme: Optional[ColorScheme] = None) -> str:
    """
    Convert ANSI color codes to HTML spans for browser rendering.
    
    Args:
        ascii_text: ASCII art string with ANSI color codes
        color_scheme: Optional ColorScheme for tinted rendering
        
    Returns:
        HTML string with <span> tags for colored characters
    """
    if not ascii_text:
        return ""
    
    if "\033" not in ascii_text:
        escaped = _escape_html(ascii_text)
        if color_scheme:
            r, g, b = color_scheme.tint
            return f'<span style="color: rgb({r}, {g}, {b})">{escaped}</span>'
        return escaped
    
    ansi_pattern = re.compile(
        r'\033\[(?:38;2;(\d+);(\d+);(\d+)|48;2;(\d+);(\d+);(\d+)|0)m'
    )
    
    result = []
    i = 0
    current_color: Optional[tuple[int, int, int]] = None
    current_bg: Optional[tuple[int, int, int]] = None
    
    for match in ansi_pattern.finditer(ascii_text):
        text_before = ascii_text[i:match.start()]
        if text_before:
            result.append(_wrap_text(text_before, current_color, current_bg, color_scheme))
        
        r, g, b = match.groups()[:3]
        bg_r, bg_g, bg_b = match.groups()[3:]
        
        if r is not None and g is not None and b is not None:
            current_color = (int(r), int(g), int(b))
        elif bg_r is not None and bg_g is not None and bg_b is not None:
            current_bg = (int(bg_r), int(bg_g), int(bg_b))
        else:
            current_color = None
            current_bg = None
        
        i = match.end()
    
    text_after = ascii_text[i:]
    if text_after:
        result.append(_wrap_text(text_after, current_color, current_bg, color_scheme))
    
    if not result and ascii_text:
        escaped = _escape_html(ascii_text)
        if color_scheme:
            r, g, b = color_scheme.tint
            return f'<span style="color: rgb({r}, {g}, {b})">{escaped}</span>'
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
    color_scheme: Optional[ColorScheme],
) -> str:
    """Wrap text in span with color styling."""
    if not text:
        return ""

    escaped = _escape_html(text)

    if color_scheme and color is None:
        color = color_scheme.tint

    styles = []
    if color:
        if color_scheme:
            cr, cg, cb = color_scheme.blend_color(*color)
            styles.append(f"color: rgb({cr}, {cg}, {cb})")
        else:
            styles.append(f"color: rgb({color[0]}, {color[1]}, {color[2]})")

    if bg:
        styles.append(f"background-color: rgb({bg[0]}, {bg[1]}, {bg[2]})")

    if styles:
        style_attr = "; ".join(styles)
        return f'<span style="{style_attr}">{escaped}</span>'
    else:
        return escaped


def frames_to_html(
    frames: list[str],
    color_scheme: Optional[ColorScheme] = None,
) -> list[str]:
    """
    Convert a list of ANSI-formatted ASCII frames to HTML.

    Args:
        frames: List of ASCII art strings (may contain ANSI codes)
        color_scheme: Optional ColorScheme for tinted rendering

    Returns:
        List of HTML strings
    """
    return [ansi_to_html(frame, color_scheme=color_scheme) for frame in frames]
