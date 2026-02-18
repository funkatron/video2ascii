"""Tests for subtitle module."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video2ascii.subtitle import (
    find_whisper_cli,
    get_whisper_model_path,
    get_vad_model_path,
    get_subtitle_for_frame,
    generate_srt,
    extract_subtitle_stream,
    probe_subtitle_stream,
    _generate_srt_whisper,
    parse_srt,
    _parse_timestamp,
    _extract_audio,
)


class TestParseTimestamp:
    """Tests for _parse_timestamp helper."""

    def test_zero(self):
        assert _parse_timestamp("00:00:00,000") == 0.0

    def test_one_second(self):
        assert _parse_timestamp("00:00:01,000") == 1.0

    def test_milliseconds(self):
        result = _parse_timestamp("00:00:01,234")
        assert abs(result - 1.234) < 0.001

    def test_minutes_and_hours(self):
        result = _parse_timestamp("01:02:03,456")
        expected = 1 * 3600.0 + 2 * 60.0 + 3.456
        assert abs(result - expected) < 0.001

    def test_with_period_separator(self):
        """SRT can use comma or period."""
        result = _parse_timestamp("00:00:01.500")
        assert abs(result - 1.5) < 0.001


class TestParseSrt:
    """Tests for parse_srt function."""

    def test_basic_srt(self, tmp_path):
        """Parse a well-formed SRT file."""
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Hello world\n"
            "\n"
            "2\n"
            "00:00:02,500 --> 00:00:05,000\n"
            "Second subtitle\n"
        )
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding="utf-8")

        segments = parse_srt(srt_file)

        assert len(segments) == 2
        assert segments[0] == (0.0, 2.0, "Hello world")
        assert abs(segments[1][0] - 2.5) < 0.001
        assert segments[1][1] == 5.0
        assert segments[1][2] == "Second subtitle"

    def test_multiline_text(self, tmp_path):
        """Multi-line subtitle text is joined with spaces."""
        srt_content = (
            "1\n"
            "00:00:00,000 --> 00:00:02,000\n"
            "Line one\n"
            "Line two\n"
        )
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding="utf-8")

        segments = parse_srt(srt_file)

        assert len(segments) == 1
        assert segments[0][2] == "Line one Line two"

    def test_empty_file(self, tmp_path):
        """Empty file returns empty list."""
        srt_file = tmp_path / "empty.srt"
        srt_file.write_text("", encoding="utf-8")

        segments = parse_srt(srt_file)
        assert segments == []

    def test_malformed_timestamp_skipped(self, tmp_path):
        """Malformed timestamps are skipped gracefully."""
        srt_content = (
            "1\n"
            "INVALID TIMESTAMP LINE\n"
            "Some text\n"
            "\n"
            "2\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Valid subtitle\n"
        )
        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content, encoding="utf-8")

        segments = parse_srt(srt_file)

        assert len(segments) == 1
        assert segments[0][2] == "Valid subtitle"

    def test_nonexistent_file(self, tmp_path):
        """Nonexistent file returns empty list."""
        segments = parse_srt(tmp_path / "does_not_exist.srt")
        assert segments == []


class TestGetSubtitleForFrame:
    """Tests for get_subtitle_for_frame function."""

    @pytest.fixture
    def sample_segments(self):
        """Two consecutive subtitle segments."""
        return [
            (0.0, 2.0, "Hello"),
            (2.0, 4.0, "World"),
        ]

    def test_first_segment(self, sample_segments):
        """Frame 0 at 12 fps -> time 0.0 -> 'Hello'."""
        result = get_subtitle_for_frame(sample_segments, 0, 12)
        assert result == "Hello"

    def test_first_segment_middle(self, sample_segments):
        """Frame 12 at 12 fps -> time 1.0 -> 'Hello'."""
        result = get_subtitle_for_frame(sample_segments, 12, 12)
        assert result == "Hello"

    def test_second_segment(self, sample_segments):
        """Frame 24 at 12 fps -> time 2.0 -> 'World'."""
        result = get_subtitle_for_frame(sample_segments, 24, 12)
        assert result == "World"

    def test_after_all_segments(self, sample_segments):
        """Frame 48 at 12 fps -> time 4.0 -> None (past end)."""
        result = get_subtitle_for_frame(sample_segments, 48, 12)
        assert result is None

    def test_gap_between_segments(self):
        """No subtitle active during a gap between segments."""
        segments = [
            (0.0, 1.0, "First"),
            (3.0, 4.0, "Second"),
        ]
        # time = 2.0 is in the gap
        result = get_subtitle_for_frame(segments, 24, 12)
        assert result is None

    def test_empty_segments(self):
        result = get_subtitle_for_frame([], 0, 12)
        assert result is None

    def test_zero_fps(self):
        segments = [(0.0, 2.0, "Hi")]
        result = get_subtitle_for_frame(segments, 0, 0)
        assert result is None


class TestFindWhisperCli:
    """Tests for find_whisper_cli function."""

    def test_env_override(self, tmp_path):
        """Environment variable overrides PATH."""
        fake_cli = tmp_path / "whisper-cli"
        fake_cli.touch()

        with patch.dict(os.environ, {"VIDEO2ASCII_WHISPER_CLI_PATH": str(fake_cli)}):
            result = find_whisper_cli()

        assert result == fake_cli

    def test_env_override_nonexistent(self, monkeypatch):
        """Env var points to nonexistent file -> falls through to PATH."""
        monkeypatch.setenv("VIDEO2ASCII_WHISPER_CLI_PATH", "/nonexistent/whisper-cli")

        with patch("video2ascii.subtitle.shutil.which", return_value=None):
            result = find_whisper_cli()

        assert result is None

    def test_found_in_path(self):
        """Falls through to shutil.which."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove env var if set
            os.environ.pop("VIDEO2ASCII_WHISPER_CLI_PATH", None)
            with patch("video2ascii.subtitle.shutil.which", return_value="/opt/homebrew/bin/whisper-cli"):
                result = find_whisper_cli()

        assert result == Path("/opt/homebrew/bin/whisper-cli")

    def test_not_found(self):
        """Returns None when not found anywhere."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("VIDEO2ASCII_WHISPER_CLI_PATH", None)
            with patch("video2ascii.subtitle.shutil.which", return_value=None):
                result = find_whisper_cli()

        assert result is None


class TestGetWhisperModelPath:
    """Tests for get_whisper_model_path function."""

    def test_video2ascii_env(self, tmp_path):
        """VIDEO2ASCII_WHISPER_MODEL env var takes priority."""
        model_file = tmp_path / "model.bin"
        model_file.touch()

        with patch.dict(os.environ, {"VIDEO2ASCII_WHISPER_MODEL": str(model_file)}):
            result = get_whisper_model_path()

        assert result == model_file

    def test_infomux_env_fallback(self, tmp_path):
        """INFOMUX_WHISPER_MODEL is checked when VIDEO2ASCII_WHISPER_MODEL is absent."""
        model_file = tmp_path / "model.bin"
        model_file.touch()

        env = {"INFOMUX_WHISPER_MODEL": str(model_file)}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("VIDEO2ASCII_WHISPER_MODEL", None)
            result = get_whisper_model_path()

        assert result == model_file

    def test_default_location(self, tmp_path, monkeypatch):
        """Falls through to default model path."""
        monkeypatch.delenv("VIDEO2ASCII_WHISPER_MODEL", raising=False)
        monkeypatch.delenv("INFOMUX_WHISPER_MODEL", raising=False)

        default_model = tmp_path / "ggml-base.en.bin"
        default_model.touch()

        monkeypatch.setattr(
            "video2ascii.subtitle.DEFAULT_MODEL_DIR", tmp_path,
        )

        result = get_whisper_model_path()
        assert result == default_model

    def test_not_found(self, monkeypatch):
        """Returns None when no model file found."""
        monkeypatch.delenv("VIDEO2ASCII_WHISPER_MODEL", raising=False)
        monkeypatch.delenv("INFOMUX_WHISPER_MODEL", raising=False)
        monkeypatch.setattr(
            "video2ascii.subtitle.DEFAULT_MODEL_DIR",
            Path("/nonexistent/path"),
        )

        result = get_whisper_model_path()
        assert result is None


class TestProbeSubtitleStream:
    """Tests for probe_subtitle_stream function."""

    def test_returns_true_when_subtitle_exists(self, tmp_path):
        """Returns True when ffprobe finds a subtitle stream."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "2\n"  # stream index

        with patch("video2ascii.subtitle.subprocess.run", return_value=mock_result):
            assert probe_subtitle_stream(video_path) is True

    def test_returns_false_when_no_subtitle(self, tmp_path):
        """Returns False when ffprobe finds no subtitle streams."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""

        with patch("video2ascii.subtitle.subprocess.run", return_value=mock_result):
            assert probe_subtitle_stream(video_path) is False

    def test_returns_false_on_ffprobe_failure(self, tmp_path):
        """Returns False when ffprobe exits with error."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "error"

        with patch("video2ascii.subtitle.subprocess.run", return_value=mock_result):
            assert probe_subtitle_stream(video_path) is False

    def test_returns_false_when_ffprobe_not_found(self, tmp_path):
        """Returns False when ffprobe binary is missing."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        with patch("video2ascii.subtitle.subprocess.run", side_effect=FileNotFoundError):
            assert probe_subtitle_stream(video_path) is False

    def test_correct_ffprobe_args(self, tmp_path):
        """Verifies correct ffprobe arguments."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            return result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            probe_subtitle_stream(video_path)

        assert "ffprobe" in captured_cmd[0]
        assert "-select_streams" in captured_cmd
        assert "s" in captured_cmd  # subtitle stream selector


class TestExtractSubtitleStream:
    """Tests for extract_subtitle_stream function."""

    def test_success(self, tmp_path):
        """Returns SRT path when extraction succeeds."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        def mock_run(cmd, **kwargs):
            # Create the output SRT file ffmpeg would produce
            srt_path = tmp_path / "embedded_subtitle.srt"
            srt_path.write_text(
                "1\n00:00:01,000 --> 00:00:03,000\nExisting sub\n",
                encoding="utf-8",
            )
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            result = extract_subtitle_stream(video_path, tmp_path)

        assert result is not None
        assert result.name == "embedded_subtitle.srt"

    def test_returns_none_on_failure(self, tmp_path):
        """Returns None when ffmpeg fails."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "no subtitle stream"

        with patch("video2ascii.subtitle.subprocess.run", return_value=mock_result):
            result = extract_subtitle_stream(video_path, tmp_path)

        assert result is None

    def test_returns_none_when_output_empty(self, tmp_path):
        """Returns None when ffmpeg produces a zero-byte file."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        def mock_run(cmd, **kwargs):
            # Create empty output file
            (tmp_path / "embedded_subtitle.srt").touch()
            result = MagicMock()
            result.returncode = 0
            return result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            result = extract_subtitle_stream(video_path, tmp_path)

        assert result is None

    def test_correct_ffmpeg_args(self, tmp_path):
        """Verifies correct ffmpeg arguments for subtitle extraction."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            result = MagicMock()
            result.returncode = 1
            result.stderr = ""
            return result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            extract_subtitle_stream(video_path, tmp_path)

        assert "ffmpeg" in captured_cmd[0]
        assert "-y" in captured_cmd
        assert "-map" in captured_cmd
        assert "0:s:0" in captured_cmd
        assert "srt" in captured_cmd


class TestGenerateSrt:
    """Tests for generate_srt function (orchestrator)."""

    def test_prefers_embedded_subtitle(self, tmp_path):
        """Uses embedded subtitle when available, skips whisper entirely."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        embedded_srt = tmp_path / "embedded_subtitle.srt"
        embedded_srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nEmbedded sub\n",
            encoding="utf-8",
        )

        with patch("video2ascii.subtitle.probe_subtitle_stream", return_value=True):
            with patch("video2ascii.subtitle.extract_subtitle_stream", return_value=embedded_srt):
                with patch("video2ascii.subtitle._generate_srt_whisper") as mock_whisper:
                    result = generate_srt(video_path, tmp_path)

        assert result == embedded_srt
        mock_whisper.assert_not_called()

    def test_falls_back_to_whisper_when_no_embedded(self, tmp_path):
        """Falls back to whisper when no embedded subtitle stream exists."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        whisper_srt = tmp_path / "transcript.srt"
        whisper_srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nWhisper sub\n",
            encoding="utf-8",
        )

        with patch("video2ascii.subtitle.probe_subtitle_stream", return_value=False):
            with patch("video2ascii.subtitle._generate_srt_whisper", return_value=whisper_srt):
                result = generate_srt(video_path, tmp_path)

        assert result == whisper_srt

    def test_falls_back_to_whisper_when_extraction_fails(self, tmp_path):
        """Falls back to whisper when embedded extraction fails."""
        video_path = tmp_path / "video.mkv"
        video_path.touch()

        whisper_srt = tmp_path / "transcript.srt"
        whisper_srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,000\nWhisper sub\n",
            encoding="utf-8",
        )

        with patch("video2ascii.subtitle.probe_subtitle_stream", return_value=True):
            with patch("video2ascii.subtitle.extract_subtitle_stream", return_value=None):
                with patch("video2ascii.subtitle._generate_srt_whisper", return_value=whisper_srt):
                    result = generate_srt(video_path, tmp_path)

        assert result == whisper_srt

    def test_returns_none_when_both_fail(self, tmp_path):
        """Returns None when both embedded and whisper fail."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        with patch("video2ascii.subtitle.probe_subtitle_stream", return_value=False):
            with patch("video2ascii.subtitle._generate_srt_whisper", return_value=None):
                result = generate_srt(video_path, tmp_path)

        assert result is None


class TestGenerateSrtWhisper:
    """Tests for _generate_srt_whisper function (whisper-cli path)."""

    def test_success(self, tmp_path):
        """Successful generation returns SRT path."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        expected_srt = tmp_path / "transcript.srt"

        def mock_run(cmd, **kwargs):
            """Mock both ffmpeg and whisper-cli."""
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0] == "ffmpeg":
                audio_path = tmp_path / "audio_for_whisper.wav"
                audio_path.touch()
            elif "whisper-cli" in str(cmd[0]):
                expected_srt.write_text(
                    "1\n00:00:00,000 --> 00:00:02,000\nHello\n",
                    encoding="utf-8",
                )

            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
                with patch("video2ascii.subtitle.get_whisper_model_path", return_value=Path("/model.bin")):
                    result = _generate_srt_whisper(video_path, tmp_path)

        assert result is not None
        assert result.name == "transcript.srt"

    def test_no_whisper_cli(self, tmp_path):
        """Returns None when whisper-cli not found."""
        with patch("video2ascii.subtitle.find_whisper_cli", return_value=None):
            result = _generate_srt_whisper(tmp_path / "video.mp4", tmp_path)

        assert result is None

    def test_no_model(self, tmp_path):
        """Returns None when model not found."""
        with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
            with patch("video2ascii.subtitle.get_whisper_model_path", return_value=None):
                result = _generate_srt_whisper(tmp_path / "video.mp4", tmp_path)

        assert result is None

    def test_ffmpeg_extraction_fails(self, tmp_path):
        """Returns None when audio extraction fails."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        def mock_run(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stderr = "ffmpeg error"
            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
                with patch("video2ascii.subtitle.get_whisper_model_path", return_value=Path("/model.bin")):
                    result = _generate_srt_whisper(video_path, tmp_path)

        assert result is None

    def test_whisper_cli_fails(self, tmp_path):
        """Returns None when whisper-cli fails."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        call_count = [0]

        def mock_run(cmd, **kwargs):
            call_count[0] += 1
            mock_result = MagicMock()

            if call_count[0] == 1:
                mock_result.returncode = 0
                (tmp_path / "audio_for_whisper.wav").touch()
            else:
                mock_result.returncode = 1
                mock_result.stderr = "whisper error"

            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
                with patch("video2ascii.subtitle.get_whisper_model_path", return_value=Path("/model.bin")):
                    result = _generate_srt_whisper(video_path, tmp_path)

        assert result is None


class TestExtractAudio:
    """Tests for _extract_audio function."""

    def test_correct_ffmpeg_args(self, tmp_path):
        """Verify correct ffmpeg arguments for audio extraction."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        captured_cmd = []

        def mock_run(cmd, **kwargs):
            captured_cmd.extend(cmd)
            mock_result = MagicMock()
            mock_result.returncode = 0
            # Create the output file
            (tmp_path / "audio_for_whisper.wav").touch()
            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            result = _extract_audio(video_path, tmp_path)

        assert result is not None
        assert "ffmpeg" in captured_cmd[0]
        assert "-y" in captured_cmd
        assert "-vn" in captured_cmd
        assert "-ar" in captured_cmd
        assert "16000" in captured_cmd
        assert "-ac" in captured_cmd
        assert "1" in captured_cmd


class TestGetVadModelPath:
    """Tests for get_vad_model_path function."""

    def test_env_override(self, tmp_path):
        """VIDEO2ASCII_VAD_MODEL env var is checked first."""
        vad_file = tmp_path / "silero.bin"
        vad_file.touch()

        with patch.dict(os.environ, {"VIDEO2ASCII_VAD_MODEL": str(vad_file)}):
            result = get_vad_model_path()

        assert result == vad_file

    def test_env_override_nonexistent(self, monkeypatch):
        """Env var points to nonexistent file -> falls through."""
        monkeypatch.setenv("VIDEO2ASCII_VAD_MODEL", "/nonexistent/silero.bin")
        monkeypatch.setattr(
            "video2ascii.subtitle.DEFAULT_MODEL_DIR", Path("/nonexistent/path"),
        )

        result = get_vad_model_path()
        assert result is None

    def test_default_location(self, tmp_path, monkeypatch):
        """Falls through to default model path."""
        monkeypatch.delenv("VIDEO2ASCII_VAD_MODEL", raising=False)

        vad_file = tmp_path / "ggml-silero-v5.1.2.bin"
        vad_file.touch()

        monkeypatch.setattr("video2ascii.subtitle.DEFAULT_MODEL_DIR", tmp_path)

        result = get_vad_model_path()
        assert result == vad_file

    def test_not_found(self, monkeypatch):
        """Returns None when no VAD model found."""
        monkeypatch.delenv("VIDEO2ASCII_VAD_MODEL", raising=False)
        monkeypatch.setattr(
            "video2ascii.subtitle.DEFAULT_MODEL_DIR", Path("/nonexistent/path"),
        )

        result = get_vad_model_path()
        assert result is None


class TestWhisperCliVadFlags:
    """Tests for VAD flag integration in _generate_srt_whisper."""

    def test_vad_flags_added_when_model_available(self, tmp_path):
        """whisper-cli command includes --vad flags when VAD model exists."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        vad_model = tmp_path / "silero.bin"
        vad_model.touch()

        expected_srt = tmp_path / "transcript.srt"
        captured_cmd = []

        def mock_run(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0] == "ffmpeg":
                (tmp_path / "audio_for_whisper.wav").touch()
            elif "whisper-cli" in str(cmd[0]):
                captured_cmd.extend(cmd)
                expected_srt.write_text(
                    "1\n00:00:12,160 --> 00:00:15,720\nHello\n",
                    encoding="utf-8",
                )

            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
                with patch("video2ascii.subtitle.get_whisper_model_path", return_value=Path("/model.bin")):
                    with patch("video2ascii.subtitle.get_vad_model_path", return_value=vad_model):
                        _generate_srt_whisper(video_path, tmp_path)

        assert "--vad" in captured_cmd
        assert "--vad-model" in captured_cmd
        assert str(vad_model) in captured_cmd

    def test_no_vad_flags_when_model_missing(self, tmp_path):
        """whisper-cli command omits --vad flags when VAD model not found."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        expected_srt = tmp_path / "transcript.srt"
        captured_cmd = []

        def mock_run(cmd, **kwargs):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stderr = ""

            if cmd[0] == "ffmpeg":
                (tmp_path / "audio_for_whisper.wav").touch()
            elif "whisper-cli" in str(cmd[0]):
                captured_cmd.extend(cmd)
                expected_srt.write_text(
                    "1\n00:00:00,000 --> 00:00:15,000\nHello\n",
                    encoding="utf-8",
                )

            return mock_result

        with patch("video2ascii.subtitle.subprocess.run", side_effect=mock_run):
            with patch("video2ascii.subtitle.find_whisper_cli", return_value=Path("/usr/bin/whisper-cli")):
                with patch("video2ascii.subtitle.get_whisper_model_path", return_value=Path("/model.bin")):
                    with patch("video2ascii.subtitle.get_vad_model_path", return_value=None):
                        _generate_srt_whisper(video_path, tmp_path)

        assert "--vad" not in captured_cmd
        assert "--vad-model" not in captured_cmd
