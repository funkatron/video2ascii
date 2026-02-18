"""Subtitle extraction and generation.

Supports two strategies (tried in order):
    1. Extract an existing subtitle stream from the video via ffmpeg/ffprobe
    2. Generate subtitles from audio via whisper-cli (whisper-cpp)

Requires:
    - ffmpeg / ffprobe (for stream probing, extraction, and audio extraction)
    - whisper-cli (brew install whisper-cpp) -- only for strategy 2
    - A GGML whisper model file -- only for strategy 2
"""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Environment variable names
ENV_WHISPER_CLI_PATH = "VIDEO2ASCII_WHISPER_CLI_PATH"
ENV_WHISPER_MODEL = "VIDEO2ASCII_WHISPER_MODEL"
ENV_INFOMUX_WHISPER_MODEL = "INFOMUX_WHISPER_MODEL"

# Default model location (shared with infomux)
DEFAULT_MODEL_DIR = Path.home() / ".local" / "share" / "infomux" / "models" / "whisper"
DEFAULT_MODEL_NAME = "ggml-base.en.bin"
DEFAULT_VAD_MODEL_NAME = "ggml-silero-v5.1.2.bin"


def find_whisper_cli() -> Optional[Path]:
    """
    Find the whisper-cli binary.

    Checks VIDEO2ASCII_WHISPER_CLI_PATH env var first, then PATH.

    Returns:
        Path to whisper-cli, or None if not found.
    """
    # Check environment variable first
    env_path = os.environ.get(ENV_WHISPER_CLI_PATH)
    if env_path:
        path = Path(env_path)
        if path.exists():
            logger.debug("found whisper-cli via %s: %s", ENV_WHISPER_CLI_PATH, path)
            return path
        else:
            logger.warning("%s set but file not found: %s", ENV_WHISPER_CLI_PATH, path)

    # Check PATH
    which_path = shutil.which("whisper-cli")
    if which_path:
        path = Path(which_path)
        logger.debug("found whisper-cli in PATH: %s", path)
        return path

    logger.debug("whisper-cli not found")
    return None


def get_whisper_model_path() -> Optional[Path]:
    """
    Find the whisper GGML model file.

    Checks (in order):
        1. VIDEO2ASCII_WHISPER_MODEL env var
        2. INFOMUX_WHISPER_MODEL env var (shared with infomux)
        3. Default location: ~/.local/share/infomux/models/whisper/ggml-base.en.bin

    Returns:
        Path to the model file, or None if not found.
    """
    # Check VIDEO2ASCII_WHISPER_MODEL
    env_path = os.environ.get(ENV_WHISPER_MODEL)
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            logger.debug("found whisper model via %s: %s", ENV_WHISPER_MODEL, path)
            return path
        else:
            logger.warning("%s set but file not found: %s", ENV_WHISPER_MODEL, path)

    # Check INFOMUX_WHISPER_MODEL (shared with infomux)
    env_path = os.environ.get(ENV_INFOMUX_WHISPER_MODEL)
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            logger.debug("found whisper model via %s: %s", ENV_INFOMUX_WHISPER_MODEL, path)
            return path
        else:
            logger.warning("%s set but file not found: %s", ENV_INFOMUX_WHISPER_MODEL, path)

    # Check default location
    default_path = DEFAULT_MODEL_DIR / DEFAULT_MODEL_NAME
    if default_path.exists():
        logger.debug("found whisper model at default location: %s", default_path)
        return default_path

    logger.debug("whisper model not found")
    return None


def get_vad_model_path() -> Optional[Path]:
    """
    Find the Silero VAD GGML model file for whisper-cli.

    Voice Activity Detection lets whisper-cli skip silence and produce
    accurate start timestamps.  Without VAD, whisper-cli begins the
    first segment at 0:00 regardless of when speech actually starts.

    Checks (in order):
        1. VIDEO2ASCII_VAD_MODEL env var
        2. Default location alongside whisper model

    Returns:
        Path to the VAD model file, or None if not found.
    """
    env_path = os.environ.get("VIDEO2ASCII_VAD_MODEL")
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            logger.debug("found VAD model via VIDEO2ASCII_VAD_MODEL: %s", path)
            return path
        else:
            logger.warning("VIDEO2ASCII_VAD_MODEL set but file not found: %s", path)

    default_path = DEFAULT_MODEL_DIR / DEFAULT_VAD_MODEL_NAME
    if default_path.exists():
        logger.debug("found VAD model at default location: %s", default_path)
        return default_path

    logger.debug("VAD model not found (subtitle start times may be inaccurate)")
    return None


def _extract_audio(video_path: Path, work_dir: Path) -> Optional[Path]:
    """
    Extract audio from video as 16kHz mono WAV using ffmpeg.

    Args:
        video_path: Path to input video file.
        work_dir: Working directory for output.

    Returns:
        Path to extracted audio WAV, or None on failure.
    """
    audio_path = work_dir / "audio_for_whisper.wav"

    cmd = [
        "ffmpeg",
        "-y",                   # Overwrite without prompting
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-vn",                  # No video
        "-acodec", "pcm_s16le", # 16-bit PCM
        "-ar", "16000",         # 16kHz sample rate (whisper requirement)
        "-ac", "1",             # Mono
        str(audio_path),
    ]

    logger.debug("extracting audio: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("ffmpeg audio extraction failed: %s", result.stderr)
            return None
    except FileNotFoundError:
        logger.error("ffmpeg not found for audio extraction")
        return None

    if not audio_path.exists():
        logger.error("audio extraction produced no output")
        return None

    logger.debug("extracted audio: %s (%d bytes)", audio_path, audio_path.stat().st_size)
    return audio_path


def probe_subtitle_stream(video_path: Path) -> bool:
    """
    Check whether the video file contains a subtitle stream.

    Uses ffprobe to inspect the container for subtitle-type streams.

    Args:
        video_path: Path to video file.

    Returns:
        True if at least one subtitle stream exists.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "s",           # subtitle streams only
        "-show_entries", "stream=index",   # just need to know if any exist
        "-of", "csv=p=0",
        str(video_path),
    ]

    logger.debug("probing for subtitle streams: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug("ffprobe failed (exit %d): %s", result.returncode, result.stderr)
            return False
    except FileNotFoundError:
        logger.debug("ffprobe not found")
        return False

    # Any non-empty output means at least one subtitle stream was found
    has_subs = bool(result.stdout.strip())
    if has_subs:
        logger.debug("found embedded subtitle stream(s)")
    else:
        logger.debug("no embedded subtitle streams")
    return has_subs


def extract_subtitle_stream(video_path: Path, work_dir: Path) -> Optional[Path]:
    """
    Extract the first subtitle stream from a video file as SRT.

    Uses ffmpeg to demux the subtitle track.  Works with SRT, ASS/SSA,
    MOV_TEXT, and other text-based subtitle codecs that ffmpeg can
    convert to SRT.

    Args:
        video_path: Path to input video file.
        work_dir: Working directory for output.

    Returns:
        Path to extracted SRT file, or None on failure.
    """
    srt_path = work_dir / "embedded_subtitle.srt"

    cmd = [
        "ffmpeg",
        "-y",                  # Overwrite without prompting
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(video_path),
        "-map", "0:s:0",       # first subtitle stream
        "-c:s", "srt",         # convert to SRT format
        str(srt_path),
    ]

    logger.debug("extracting subtitle stream: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.debug("ffmpeg subtitle extraction failed: %s", result.stderr)
            return None
    except FileNotFoundError:
        logger.debug("ffmpeg not found for subtitle extraction")
        return None

    if not srt_path.exists() or srt_path.stat().st_size == 0:
        logger.debug("subtitle extraction produced no output")
        return None

    logger.info(
        "Extracted embedded subtitles: %s (%d bytes)",
        srt_path.name, srt_path.stat().st_size,
    )
    return srt_path


def _generate_srt_whisper(video_path: Path, work_dir: Path) -> Optional[Path]:
    """
    Generate SRT subtitles by transcribing audio with whisper-cli.

    Extracts audio with ffmpeg, then runs whisper-cli to produce an SRT file.

    Args:
        video_path: Path to input video file.
        work_dir: Working directory for intermediate and output files.

    Returns:
        Path to generated transcript.srt, or None on failure.
    """
    whisper_cli = find_whisper_cli()
    if not whisper_cli:
        logger.warning(
            "whisper-cli not found, skipping subtitle generation. "
            "Install via: brew install whisper-cpp"
        )
        return None

    model_path = get_whisper_model_path()
    if not model_path:
        logger.warning(
            "Whisper model not found, skipping subtitle generation. "
            "Set %s or place model at: %s",
            ENV_WHISPER_MODEL,
            DEFAULT_MODEL_DIR / DEFAULT_MODEL_NAME,
        )
        return None

    # Extract audio from video
    logger.info("Extracting audio for subtitle generation...")
    audio_path = _extract_audio(video_path, work_dir)
    if not audio_path:
        logger.error("Failed to extract audio, skipping subtitle generation")
        return None

    # Run whisper-cli
    output_prefix = work_dir / "transcript"

    cmd = [
        str(whisper_cli),
        "-m", str(model_path),
        "-f", str(audio_path),
        "-of", str(output_prefix),
        "-osrt",    # Generate SRT output
        "-np",      # No progress output
    ]

    # Enable Voice Activity Detection if the Silero VAD model is available.
    # This gives whisper-cli accurate speech boundaries so the first segment
    # starts when speech actually begins, not at 0:00.
    vad_model = get_vad_model_path()
    if vad_model:
        cmd.extend(["--vad", "--vad-model", str(vad_model)])
        logger.info("VAD enabled (model: %s)", vad_model.name)
    else:
        logger.info(
            "VAD model not found -- subtitle start times may be inaccurate. "
            "Download from: https://huggingface.co/ggml-org/silero-v5.1.2"
        )

    logger.info("Transcribing audio with whisper-cli...")
    logger.debug("running: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error("whisper-cli failed (exit %d): %s", result.returncode, result.stderr)
            return None
    except FileNotFoundError:
        logger.error("whisper-cli not found at: %s", whisper_cli)
        return None

    srt_path = Path(str(output_prefix) + ".srt")
    if not srt_path.exists():
        logger.error("whisper-cli produced no SRT output")
        return None

    logger.info("Generated subtitles: %s (%d bytes)", srt_path.name, srt_path.stat().st_size)

    return srt_path


def generate_srt(video_path: Path, work_dir: Path) -> Optional[Path]:
    """
    Obtain SRT subtitles for a video file.

    Tries two strategies in order:
        1. Extract an existing subtitle stream from the video container
        2. Generate subtitles from audio via whisper-cli

    Args:
        video_path: Path to input video file.
        work_dir: Working directory for intermediate and output files.

    Returns:
        Path to SRT file, or None on failure.
    """
    # Strategy 1: use embedded subtitle stream if available
    if probe_subtitle_stream(video_path):
        logger.info("Found embedded subtitle stream, extracting...")
        srt_path = extract_subtitle_stream(video_path, work_dir)
        if srt_path:
            return srt_path
        logger.warning("Embedded subtitle extraction failed, falling back to whisper")

    # Strategy 2: transcribe audio with whisper-cli
    return _generate_srt_whisper(video_path, work_dir)


def _parse_timestamp(timestamp_str: str) -> float:
    """
    Parse SRT timestamp format (HH:MM:SS,mmm) to seconds.

    Args:
        timestamp_str: Timestamp string like "00:00:01,234"

    Returns:
        Time in seconds as float.
    """
    # Replace comma with period for float parsing
    time_str = timestamp_str.strip().replace(",", ".")
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600.0 + minutes * 60.0 + seconds


def parse_srt(srt_path: Path) -> list[tuple[float, float, str]]:
    """
    Parse an SRT file into subtitle segments.

    Args:
        srt_path: Path to SRT file.

    Returns:
        List of (start_sec, end_sec, text) tuples.
    """
    segments: list[tuple[float, float, str]] = []

    try:
        content = srt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.error("Failed to read SRT file %s: %s", srt_path, e)
        return segments

    # SRT format: blocks separated by blank lines
    # Each block: sequence number, timestamp line, text line(s)
    blocks = re.split(r"\n\s*\n", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Line 0: sequence number (skip)
        # Line 1: timestamps "HH:MM:SS,mmm --> HH:MM:SS,mmm"
        timestamp_line = lines[1].strip()
        match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,.]\d{3})",
            timestamp_line,
        )
        if not match:
            logger.debug("skipping malformed timestamp line: %s", timestamp_line)
            continue

        try:
            start_sec = _parse_timestamp(match.group(1))
            end_sec = _parse_timestamp(match.group(2))
        except (ValueError, IndexError) as e:
            logger.debug("skipping unparseable timestamp: %s", e)
            continue

        # Lines 2+: subtitle text (may be multi-line)
        text = " ".join(line.strip() for line in lines[2:] if line.strip())
        if text:
            segments.append((start_sec, end_sec, text))

    logger.debug("parsed %d subtitle segments from %s", len(segments), srt_path.name)
    return segments


def get_subtitle_for_frame(
    segments: list[tuple[float, float, str]],
    frame_index: int,
    fps: int,
) -> Optional[str]:
    """
    Get the active subtitle text for a given frame.

    Args:
        segments: Parsed subtitle segments from parse_srt().
        frame_index: Zero-based frame index.
        fps: Frames per second of the video.

    Returns:
        Subtitle text string, or None if no subtitle is active.
    """
    if not segments or fps <= 0:
        return None

    time_sec = frame_index / fps

    for start_sec, end_sec, text in segments:
        if start_sec <= time_sec < end_sec:
            return text

    return None
