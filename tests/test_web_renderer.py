"""Tests for web renderer module."""

import pytest

from video2ascii.web.renderer import ansi_to_html, frames_to_html


class TestAnsiToHtml:
    """Tests for ANSI to HTML conversion."""

    def test_plain_text(self):
        """Test plain text without ANSI codes."""
        text = "Hello World"
        result = ansi_to_html(text)
        assert result == "Hello World"

    def test_ansi_color_codes(self):
        """Test ANSI color code conversion."""
        text = "\033[38;2;255;0;0mRed\033[0m"
        result = ansi_to_html(text)
        assert "rgb(255, 0, 0)" in result
        assert "Red" in result
        assert "<span" in result

    def test_ansi_reset(self):
        """Test ANSI reset code."""
        text = "\033[38;2;0;255;0mGreen\033[0mNormal"
        result = ansi_to_html(text)
        assert "rgb(0, 255, 0)" in result
        assert "Green" in result
        assert "Normal" in result

    def test_html_escaping(self):
        """Test that HTML special characters are escaped."""
        text = "<script>alert('xss')</script>"
        result = ansi_to_html(text)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_crt_mode(self):
        """Test CRT green phosphor mode."""
        text = "Hello"
        result = ansi_to_html(text, crt=True)
        assert "rgb(51, 255, 51)" in result or "color:" in result

    def test_multiple_colors(self):
        """Test multiple color codes in one string."""
        text = "\033[38;2;255;0;0mRed\033[0m \033[38;2;0;0;255mBlue\033[0m"
        result = ansi_to_html(text)
        assert "rgb(255, 0, 0)" in result
        assert "rgb(0, 0, 255)" in result

    def test_empty_string(self):
        """Test empty string."""
        result = ansi_to_html("")
        assert result == ""

    def test_newlines_preserved(self):
        """Test that newlines are preserved."""
        text = "Line 1\nLine 2"
        result = ansi_to_html(text)
        assert "\n" in result


class TestFramesToHtml:
    """Tests for frames_to_html function."""

    def test_single_frame(self):
        """Test converting a single frame."""
        frames = ["Hello World"]
        result = frames_to_html(frames)
        assert len(result) == 1
        assert "Hello World" in result[0]

    def test_multiple_frames(self):
        """Test converting multiple frames."""
        frames = ["Frame 1", "Frame 2", "Frame 3"]
        result = frames_to_html(frames)
        assert len(result) == 3
        assert "Frame 1" in result[0]
        assert "Frame 2" in result[1]
        assert "Frame 3" in result[2]

    def test_colored_frames(self):
        """Test converting frames with ANSI codes."""
        frames = ["\033[38;2;255;0;0mRed\033[0m"]
        result = frames_to_html(frames)
        assert len(result) == 1
        assert "rgb(255, 0, 0)" in result[0]

    def test_crt_mode(self):
        """Test CRT mode for frames."""
        frames = ["Hello"]
        result = frames_to_html(frames, crt=True)
        assert len(result) == 1
        # Should have CRT green tint
        assert "color:" in result[0] or "rgb(51, 255, 51)" in result[0]

    def test_empty_frames_list(self):
        """Test empty frames list."""
        result = frames_to_html([])
        assert result == []
