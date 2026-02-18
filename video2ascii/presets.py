"""Preset definitions for video2ascii.

Each preset bundles conversion settings and an optional color scheme.
This is the single source of truth used by both the CLI (--preset) and
the web UI (/api/presets).
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ColorScheme:
    """Color scheme for tinted rendering (CRT green, C64 blue, etc.).

    Attributes:
        tint: RGB tuple for text tint color.
        bg: RGB tuple for background color.
        blend: Tint blend strength (0.0 = no tint, 1.0 = full tint).
    """
    tint: tuple[int, int, int]
    bg: tuple[int, int, int]
    blend: float = 0.8

    def to_dict(self) -> dict:
        """Serialize for JSON (web API)."""
        return {"tint": list(self.tint), "bg": list(self.bg), "blend": self.blend}

    @classmethod
    def from_dict(cls, data: dict) -> "ColorScheme":
        """Deserialize from JSON dict."""
        return cls(
            tint=tuple(data["tint"]),
            bg=tuple(data["bg"]),
            blend=data.get("blend", 0.8),
        )

    def blend_color(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """Blend an RGB color with this scheme's tint.

        Uses the scheme's blend factor: result = original * (1-blend) + tint * blend.
        """
        tr, tg, tb = self.tint
        inv = 1.0 - self.blend
        return (
            min(255, int(r * inv + tr * self.blend)),
            min(255, int(g * inv + tg * self.blend)),
            min(255, int(b * inv + tb * self.blend)),
        )


# Named color schemes
CRT_GREEN = ColorScheme(tint=(51, 255, 51), bg=(5, 5, 5))
C64_BLUE = ColorScheme(tint=(124, 112, 218), bg=(53, 40, 121))


PRESETS: dict[str, dict] = {
    "classic": {
        "width": 160,
        "fps": 12,
        "charset": "classic",
        "color": False,
        "invert": False,
        "edge": False,
    },
    "crt": {
        "width": 80,
        "fps": 12,
        "charset": "classic",
        "color": True,
        "invert": False,
        "edge": False,
        "color_scheme": CRT_GREEN,
        "crt_filter": True,
    },
    "c64": {
        "width": 40,
        "fps": 12,
        "charset": "petscii",
        "color": True,
        "invert": False,
        "edge": False,
        "color_scheme": C64_BLUE,
        "crt_filter": True,
    },
    "sketch": {
        "width": 160,
        "fps": 12,
        "charset": "classic",
        "color": False,
        "invert": True,
        "edge": True,
    },
    "minimal": {
        "width": 120,
        "fps": 10,
        "charset": "simple",
        "color": False,
        "invert": False,
        "edge": False,
    },
}


def get_color_scheme(preset_name: str) -> Optional[ColorScheme]:
    """Return the ColorScheme for a preset, or None if it has no scheme."""
    preset = PRESETS.get(preset_name)
    if preset is None:
        return None
    return preset.get("color_scheme")


def serialize_presets() -> dict[str, dict]:
    """Serialize PRESETS for JSON transport (web API).

    ColorScheme objects are converted to plain dicts.
    """
    result = {}
    for name, preset in PRESETS.items():
        entry = dict(preset)
        scheme = entry.pop("color_scheme", None)
        if scheme is not None:
            entry["color_scheme"] = scheme.to_dict()
        result[name] = entry
    return result
