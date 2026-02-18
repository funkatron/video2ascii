"""Font discovery and resolution for MP4/ProRes export.

Centralises all font-finding logic so that mp4_exporter.py doesn't have to
care about where fonts live on disk.  The main entry points are:

    resolve_font(charset, font_override) -> ResolvedFont
    list_available_fonts(charset) -> list[str]
    get_subtitle_font_name() -> str
"""

import functools
import logging
from pathlib import Path
from typing import NamedTuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font search directories (platform-ordered)
# ---------------------------------------------------------------------------

FONT_SEARCH_DIRS: list[Path] = [
    Path.home() / "Library/Fonts",         # macOS user
    Path("/Library/Fonts"),                 # macOS system
    Path("/System/Library/Fonts"),          # macOS built-in
    Path.home() / ".fonts",                 # Linux user (legacy)
    Path.home() / ".local/share/fonts",     # Linux user (XDG)
    Path("/usr/share/fonts/truetype"),      # Linux system
    Path("/usr/share/fonts/TTF"),           # Arch Linux
    Path("/usr/share/fonts/opentype"),      # Linux OTF
    Path("/mnt/c/Windows/Fonts"),           # WSL
]

# ---------------------------------------------------------------------------
# PetMe font variants (ordered by preference for PETSCII charset)
# ---------------------------------------------------------------------------

PETME_VARIANTS: list[str] = [
    "PetMe64",
    "PetMe",
    "PetMe128",
    "PetMe2X",
    "PetMe2Y",
    "PetMe642Y",
    "PetMe1282Y",
]

# ---------------------------------------------------------------------------
# Return type for resolve_font()
# ---------------------------------------------------------------------------

class ResolvedFont(NamedTuple):
    """Result of font resolution.

    Attributes:
        path: Filesystem path to the font file, or None for Pillow default.
        is_bold: True if the font is a bold variant (controls braille
                 stroke-effect rendering).
    """
    path: Optional[Path]
    is_bold: bool


# ---------------------------------------------------------------------------
# Private helpers (moved from mp4_exporter.py)
# ---------------------------------------------------------------------------

def _find_monospace_font() -> Optional[Path]:
    """Find a general-purpose monospace font on the system.

    PetMe fonts are intentionally excluded -- they belong in the PETSCII
    path only, not the general fallback.
    """
    logger.debug("Searching for monospace font...")
    font_paths = [
        # Iosevka - popular monospace font
        Path.home() / "Library/Fonts/Iosevka-Regular.ttf",
        Path("/Library/Fonts/Iosevka-Regular.ttf"),
        Path.home() / ".fonts/Iosevka-Regular.ttf",
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Regular.ttf"),
        Path.home() / ".local/share/fonts/Iosevka-Regular.ttf",
        # VT323 - retro terminal font
        Path.home() / "Library/Fonts/VT323-Regular.ttf",
        Path("/Library/Fonts/VT323-Regular.ttf"),
        Path.home() / ".fonts/VT323-Regular.ttf",
        Path("/usr/share/fonts/truetype/vt323/VT323-Regular.ttf"),
        Path.home() / ".local/share/fonts/VT323-Regular.ttf",
        # IBM Plex Mono - professional monospace
        Path.home() / "Library/Fonts/IBMPlexMono-Regular.ttf",
        Path("/Library/Fonts/IBMPlexMono-Regular.ttf"),
        Path.home() / ".fonts/IBMPlexMono-Regular.ttf",
        Path("/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Regular.ttf"),
        Path.home() / ".local/share/fonts/IBMPlexMono-Regular.ttf",
        Path("/usr/share/fonts/opentype/ibm/plex/IBMPlexMono-Regular.otf"),
        # macOS system fonts
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Courier.ttc"),
        Path("/Library/Fonts/Courier New.ttf"),
        # Linux system fonts
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        # Windows (WSL)
        Path("/mnt/c/Windows/Fonts/consola.ttf"),
        Path("/mnt/c/Windows/Fonts/cour.ttf"),
    ]

    for font_path in font_paths:
        if font_path.exists():
            logger.debug("Found monospace font: %s", font_path)
            return font_path

    logger.warning("No monospace font found, using default")
    return None


def _find_braille_font() -> Optional[Path]:
    """Find a font that supports braille Unicode characters (U+2800-U+28FF)."""
    logger.debug("Searching for braille-supporting font...")
    braille_font_paths = [
        Path("/System/Library/Fonts/Apple Braille.ttf"),
        Path("/System/Library/Fonts/Apple Braille Outline 8 Dot.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        Path.home() / ".fonts/DejaVuSansMono.ttf",
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/System/Library/Fonts/Courier.ttc"),
        Path("/Library/Fonts/Courier New.ttf"),
        Path.home() / "Library/Fonts/Iosevka-Regular.ttf",
        Path("/Library/Fonts/Iosevka-Regular.ttf"),
        Path.home() / ".fonts/Iosevka-Regular.ttf",
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Regular.ttf"),
    ]

    for font_path in braille_font_paths:
        if font_path.exists():
            logger.debug("Found braille font: %s", font_path)
            return font_path

    logger.warning("No braille-supporting font found")
    return None


def _find_bold_braille_font() -> Optional[Path]:
    """Find a bold font variant that supports braille Unicode characters."""
    logger.debug("Searching for bold braille font...")
    bold_braille_font_paths = [
        Path("/System/Library/Fonts/Apple Braille Bold.ttf"),
        Path("/System/Library/Fonts/Apple Braille Outline 8 Dot Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf"),
        Path.home() / ".fonts/DejaVuSansMono-Bold.ttf",
        Path("/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf"),
        Path("/System/Library/Fonts/Menlo Bold.ttc"),
        Path("/System/Library/Fonts/Courier Bold.ttc"),
        Path("/Library/Fonts/Courier New Bold.ttf"),
        Path.home() / "Library/Fonts/Iosevka-Bold.ttf",
        Path("/Library/Fonts/Iosevka-Bold.ttf"),
        Path.home() / ".fonts/Iosevka-Bold.ttf",
        Path("/usr/share/fonts/truetype/iosevka/Iosevka-Bold.ttf"),
    ]

    for font_path in bold_braille_font_paths:
        if font_path.exists():
            logger.debug("Found bold braille font: %s", font_path)
            return font_path

    logger.debug("No bold braille font found")
    return None


def _find_petme_font(variant: Optional[str] = None) -> Optional[Path]:
    """Find a PetMe font file.

    Args:
        variant: Specific variant name (e.g. "PetMe128").  If None, tries
                 all PETME_VARIANTS in order.

    Returns:
        Path to font file, or None.
    """
    variants = [variant] if variant else PETME_VARIANTS

    for name in variants:
        filename = f"{name}.ttf"
        for search_dir in FONT_SEARCH_DIRS:
            candidate = search_dir / filename
            if candidate.exists():
                logger.debug("Found PetMe font: %s", candidate)
                return candidate

    logger.debug("No PetMe font found")
    return None


def _resolve_by_name(name: str) -> Optional[Path]:
    """Resolve a bare font name (e.g. "PetMe128") to a file path.

    Searches FONT_SEARCH_DIRS for ``{name}.ttf`` and ``{name}.ttc``.
    """
    for ext in (".ttf", ".ttc", ".otf"):
        filename = f"{name}{ext}"
        for search_dir in FONT_SEARCH_DIRS:
            candidate = search_dir / filename
            if candidate.exists():
                logger.debug("Resolved font name '%s' -> %s", name, candidate)
                return candidate

    logger.warning("Font '%s' not found in any search directory", name)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_font(
    charset: str,
    font_override: Optional[str] = None,
) -> ResolvedFont:
    """Resolve which font file to use for image rendering.

    Args:
        charset: Active character set name (e.g. "petscii", "braille",
                 "classic").
        font_override: User-supplied font.  Can be:
            - An absolute path (``/path/to/font.ttf``) -- used directly.
            - A bare name (``PetMe128``) -- resolved via FONT_SEARCH_DIRS.
            - ``None`` -- auto-select based on charset.

    Returns:
        ResolvedFont(path, is_bold).
    """
    # --- Explicit override ---------------------------------------------------
    if font_override:
        override_path = Path(font_override)
        if override_path.is_absolute() and override_path.exists():
            logger.info("Using font override (absolute): %s", override_path)
            return ResolvedFont(path=override_path, is_bold=False)

        # Treat as bare name
        resolved = _resolve_by_name(font_override)
        if resolved:
            logger.info("Using font override (resolved): %s", resolved)
            return ResolvedFont(path=resolved, is_bold=False)

        logger.warning(
            "Font override '%s' not found, falling back to auto-select",
            font_override,
        )

    # --- Auto-select based on charset ----------------------------------------
    charset_lower = charset.lower()

    if charset_lower == "petscii":
        path = _find_petme_font()
        if path:
            return ResolvedFont(path=path, is_bold=False)
        # Fall through to general monospace
        logger.debug("No PetMe font found, falling back to monospace")

    if charset_lower == "braille":
        bold = _find_bold_braille_font()
        if bold:
            return ResolvedFont(path=bold, is_bold=True)
        regular = _find_braille_font()
        if regular:
            return ResolvedFont(path=regular, is_bold=False)
        # Fall through to general monospace
        logger.debug("No braille font found, falling back to monospace")

    path = _find_monospace_font()
    return ResolvedFont(path=path, is_bold=False)


@functools.lru_cache(maxsize=None)
def list_available_fonts(charset: str) -> list[str]:
    """Return names of installed fonts relevant to a charset.

    For ``petscii``, returns the names of installed PetMe variants.
    For other charsets, returns an empty list (no font choice applicable).

    Results are cached because font installations don't change at runtime.

    Args:
        charset: Character set name.

    Returns:
        List of font names (suitable for passing back as ``font_override``).
    """
    charset_lower = charset.lower()
    if charset_lower != "petscii":
        return []

    installed: list[str] = []
    for variant in PETME_VARIANTS:
        if _find_petme_font(variant) is not None:
            installed.append(variant)

    logger.debug("Installed PetMe fonts: %s", installed)
    return installed


def get_subtitle_font_name() -> str:
    """Get a monospace font family name for ffmpeg subtitle burn-in.

    Tries readable monospace fonts in priority order.  Uses the font
    family name that ffmpeg's libass (via fontconfig/CoreText) expects.

    Subtitle text needs a legible, standard monospace font -- not
    specialty fonts like PetMe 64 that are optimised for ASCII art
    rendering.

    Returns:
        Font family name string (falls back to ``"Courier"``).
    """
    candidates: list[tuple[str, list[Path]]] = [
        ("Iosevka", [
            Path.home() / "Library/Fonts/Iosevka-Regular.ttf",
            Path("/Library/Fonts/Iosevka-Regular.ttf"),
            Path.home() / ".fonts/Iosevka-Regular.ttf",
            Path("/usr/share/fonts/truetype/iosevka/Iosevka-Regular.ttf"),
            Path.home() / ".local/share/fonts/Iosevka-Regular.ttf",
        ]),
        ("IBM Plex Mono", [
            Path.home() / "Library/Fonts/IBMPlexMono-Regular.ttf",
            Path("/Library/Fonts/IBMPlexMono-Regular.ttf"),
            Path.home() / ".fonts/IBMPlexMono-Regular.ttf",
            Path("/usr/share/fonts/truetype/ibm-plex/IBMPlexMono-Regular.ttf"),
            Path.home() / ".local/share/fonts/IBMPlexMono-Regular.ttf",
        ]),
        ("Menlo", [
            Path("/System/Library/Fonts/Menlo.ttc"),
        ]),
        ("DejaVu Sans Mono", [
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
            Path.home() / ".fonts/DejaVuSansMono.ttf",
        ]),
        ("Liberation Mono", [
            Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
        ]),
        ("Courier New", [
            Path("/Library/Fonts/Courier New.ttf"),
            Path("/mnt/c/Windows/Fonts/cour.ttf"),
        ]),
        ("Courier", [
            Path("/System/Library/Fonts/Courier.ttc"),
        ]),
        ("Consolas", [
            Path("/mnt/c/Windows/Fonts/consola.ttf"),
        ]),
    ]

    for family_name, paths in candidates:
        for path in paths:
            if path.exists():
                logger.debug("subtitle font: %s (%s)", family_name, path)
                return family_name

    return "Courier"
