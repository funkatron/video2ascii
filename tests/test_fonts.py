"""Tests for fonts module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from video2ascii.fonts import (
    PETME_VARIANTS,
    ResolvedFont,
    get_subtitle_font_name,
    list_available_fonts,
    resolve_font,
)


class TestResolveFont:
    """Tests for resolve_font()."""

    def test_absolute_path_override(self, tmp_path):
        """Test resolve_font with an absolute path that exists."""
        font_file = tmp_path / "CustomFont.ttf"
        font_file.touch()

        result = resolve_font("classic", font_override=str(font_file))

        assert result.path == font_file
        assert result.is_bold is False

    def test_absolute_path_override_nonexistent_falls_back(self):
        """Test resolve_font falls back when absolute path doesn't exist."""
        result = resolve_font("classic", font_override="/nonexistent/path/Font.ttf")

        # Should fall back to auto-select (may or may not find a font)
        assert isinstance(result, ResolvedFont)

    def test_bare_name_override(self, tmp_path):
        """Test resolve_font resolves a bare name via FONT_SEARCH_DIRS."""
        font_file = tmp_path / "MyFont.ttf"
        font_file.touch()

        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", [tmp_path]):
            result = resolve_font("classic", font_override="MyFont")

        assert result.path == font_file
        assert result.is_bold is False

    def test_bare_name_override_not_found_falls_back(self):
        """Test bare name that doesn't exist falls back to auto-select."""
        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", []):
            result = resolve_font("classic", font_override="NoSuchFont")

        assert isinstance(result, ResolvedFont)

    def test_auto_select_petscii(self, tmp_path):
        """Test auto-select for petscii charset finds PetMe font."""
        petme_file = tmp_path / "PetMe64.ttf"
        petme_file.touch()

        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", [tmp_path]):
            result = resolve_font("petscii")

        assert result.path == petme_file
        assert result.is_bold is False

    def test_auto_select_petscii_fallback_to_monospace(self):
        """Test petscii falls back to monospace when no PetMe font found."""
        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", []):
            result = resolve_font("petscii")

        # Should return _something_ (either a system monospace or None)
        assert isinstance(result, ResolvedFont)

    def test_auto_select_braille_prefers_bold(self, tmp_path):
        """Test braille charset prefers bold braille font."""
        bold_braille = tmp_path / "DejaVuSansMono-Bold.ttf"
        bold_braille.touch()

        with patch(
            "video2ascii.fonts._find_bold_braille_font", return_value=bold_braille
        ):
            result = resolve_font("braille")

        assert result.path == bold_braille
        assert result.is_bold is True

    def test_auto_select_braille_regular_fallback(self, tmp_path):
        """Test braille falls back to regular braille font when no bold."""
        regular_braille = tmp_path / "DejaVuSansMono.ttf"
        regular_braille.touch()

        with patch("video2ascii.fonts._find_bold_braille_font", return_value=None):
            with patch(
                "video2ascii.fonts._find_braille_font",
                return_value=regular_braille,
            ):
                result = resolve_font("braille")

        assert result.path == regular_braille
        assert result.is_bold is False

    def test_auto_select_classic(self):
        """Test classic charset uses general monospace search."""
        result = resolve_font("classic")
        assert isinstance(result, ResolvedFont)
        # is_bold should be False for classic
        assert result.is_bold is False

    def test_return_type(self):
        """Test resolve_font always returns a ResolvedFont namedtuple."""
        result = resolve_font("classic")
        assert isinstance(result, ResolvedFont)
        assert hasattr(result, "path")
        assert hasattr(result, "is_bold")


class TestListAvailableFonts:
    """Tests for list_available_fonts()."""

    def test_petscii_returns_installed_variants(self, tmp_path):
        """Test petscii charset returns names of installed PetMe fonts."""
        # Create some PetMe font files
        (tmp_path / "PetMe64.ttf").touch()
        (tmp_path / "PetMe128.ttf").touch()

        # Clear cache from previous tests
        list_available_fonts.cache_clear()

        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", [tmp_path]):
            result = list_available_fonts("petscii")

        assert "PetMe64" in result
        assert "PetMe128" in result
        # Variants that don't exist should not be in the list
        assert "PetMe2X" not in result

        # Clean up cache
        list_available_fonts.cache_clear()

    def test_non_petscii_returns_empty(self):
        """Test non-petscii charsets return empty list."""
        list_available_fonts.cache_clear()
        assert list_available_fonts("classic") == []
        assert list_available_fonts("braille") == []
        assert list_available_fonts("blocks") == []
        list_available_fonts.cache_clear()

    def test_results_are_cached(self, tmp_path):
        """Test list_available_fonts results are cached."""
        list_available_fonts.cache_clear()

        (tmp_path / "PetMe64.ttf").touch()

        with patch("video2ascii.fonts.FONT_SEARCH_DIRS", [tmp_path]):
            result1 = list_available_fonts("petscii")
            result2 = list_available_fonts("petscii")

        assert result1 is result2  # Same object (cached)
        list_available_fonts.cache_clear()


class TestGetSubtitleFontName:
    """Tests for get_subtitle_font_name()."""

    def test_returns_string(self):
        """Test get_subtitle_font_name returns a font family name string."""
        result = get_subtitle_font_name()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_is_courier(self):
        """Test fallback font is Courier when nothing is installed."""
        with patch("pathlib.Path.exists", return_value=False):
            result = get_subtitle_font_name()
        assert result == "Courier"
