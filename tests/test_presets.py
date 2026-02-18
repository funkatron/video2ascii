"""Tests for presets module."""

import pytest

from video2ascii.presets import (
    PRESETS,
    CRT_GREEN,
    C64_BLUE,
    ColorScheme,
    get_color_scheme,
    serialize_presets,
)


class TestColorScheme:
    """Tests for ColorScheme dataclass."""

    def test_immutable(self):
        """Test ColorScheme is frozen."""
        scheme = ColorScheme(tint=(1, 2, 3), bg=(4, 5, 6))
        with pytest.raises(AttributeError):
            scheme.tint = (9, 9, 9)

    def test_default_blend(self):
        """Test default blend factor is 0.8."""
        scheme = ColorScheme(tint=(0, 0, 0), bg=(0, 0, 0))
        assert scheme.blend == 0.8

    def test_blend_color(self):
        """Test blend_color mixes original with tint."""
        scheme = ColorScheme(tint=(0, 255, 0), bg=(0, 0, 0), blend=0.5)
        r, g, b = scheme.blend_color(200, 100, 50)
        assert r == 100   # 200*0.5 + 0*0.5
        assert g == 177   # 100*0.5 + 255*0.5 = 177.5 -> 177
        assert b == 25    # 50*0.5 + 0*0.5

    def test_blend_color_full_tint(self):
        """Test blend=1.0 gives pure tint."""
        scheme = ColorScheme(tint=(51, 255, 51), bg=(0, 0, 0), blend=1.0)
        assert scheme.blend_color(200, 100, 50) == (51, 255, 51)

    def test_blend_color_no_tint(self):
        """Test blend=0.0 gives original color."""
        scheme = ColorScheme(tint=(51, 255, 51), bg=(0, 0, 0), blend=0.0)
        assert scheme.blend_color(200, 100, 50) == (200, 100, 50)

    def test_to_dict(self):
        """Test serialization to dict."""
        scheme = ColorScheme(tint=(51, 255, 51), bg=(5, 5, 5), blend=0.8)
        d = scheme.to_dict()
        assert d == {"tint": [51, 255, 51], "bg": [5, 5, 5], "blend": 0.8}

    def test_from_dict(self):
        """Test deserialization from dict."""
        d = {"tint": [124, 112, 218], "bg": [53, 40, 121], "blend": 0.7}
        scheme = ColorScheme.from_dict(d)
        assert scheme.tint == (124, 112, 218)
        assert scheme.bg == (53, 40, 121)
        assert scheme.blend == 0.7

    def test_from_dict_default_blend(self):
        """Test from_dict uses 0.8 as default blend."""
        d = {"tint": [0, 0, 0], "bg": [0, 0, 0]}
        scheme = ColorScheme.from_dict(d)
        assert scheme.blend == 0.8

    def test_roundtrip(self):
        """Test to_dict -> from_dict roundtrip."""
        original = ColorScheme(tint=(100, 200, 150), bg=(10, 20, 30), blend=0.6)
        restored = ColorScheme.from_dict(original.to_dict())
        assert restored == original


class TestNamedSchemes:
    """Tests for named color scheme constants."""

    def test_crt_green_values(self):
        assert CRT_GREEN.tint == (51, 255, 51)
        assert CRT_GREEN.bg == (5, 5, 5)

    def test_c64_blue_values(self):
        assert C64_BLUE.tint == (124, 112, 218)
        assert C64_BLUE.bg == (53, 40, 121)


class TestPresets:
    """Tests for PRESETS dict."""

    def test_all_presets_have_required_keys(self):
        required = {"width", "fps", "charset", "color", "invert", "edge"}
        for name, preset in PRESETS.items():
            missing = required - set(preset.keys())
            assert not missing, f"Preset '{name}' missing keys: {missing}"

    def test_crt_preset_has_color_scheme(self):
        assert "color_scheme" in PRESETS["crt"]
        assert isinstance(PRESETS["crt"]["color_scheme"], ColorScheme)
        assert PRESETS["crt"]["color_scheme"] is CRT_GREEN

    def test_c64_preset_has_color_scheme(self):
        assert "color_scheme" in PRESETS["c64"]
        assert isinstance(PRESETS["c64"]["color_scheme"], ColorScheme)
        assert PRESETS["c64"]["color_scheme"] is C64_BLUE

    def test_c64_uses_petscii(self):
        assert PRESETS["c64"]["charset"] == "petscii"

    def test_c64_width_is_40(self):
        assert PRESETS["c64"]["width"] == 40

    def test_classic_has_no_color_scheme(self):
        assert "color_scheme" not in PRESETS["classic"]

    def test_sketch_has_no_color_scheme(self):
        assert "color_scheme" not in PRESETS["sketch"]

    def test_minimal_has_no_color_scheme(self):
        assert "color_scheme" not in PRESETS["minimal"]

    def test_preset_names(self):
        assert set(PRESETS.keys()) == {"classic", "crt", "c64", "sketch", "minimal"}


class TestGetColorScheme:
    """Tests for get_color_scheme helper."""

    def test_returns_scheme_for_crt(self):
        assert get_color_scheme("crt") is CRT_GREEN

    def test_returns_scheme_for_c64(self):
        assert get_color_scheme("c64") is C64_BLUE

    def test_returns_none_for_classic(self):
        assert get_color_scheme("classic") is None

    def test_returns_none_for_unknown(self):
        assert get_color_scheme("nonexistent") is None


class TestSerializePresets:
    """Tests for serialize_presets."""

    def test_returns_all_presets(self):
        result = serialize_presets()
        assert set(result.keys()) == set(PRESETS.keys())

    def test_color_scheme_serialized(self):
        result = serialize_presets()
        crt = result["crt"]
        assert "color_scheme" in crt
        assert isinstance(crt["color_scheme"], dict)
        assert crt["color_scheme"]["tint"] == [51, 255, 51]

    def test_presets_without_scheme_have_no_key(self):
        result = serialize_presets()
        assert "color_scheme" not in result["classic"]
