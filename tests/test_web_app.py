"""Tests for web app module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from video2ascii.presets import CRT_GREEN, C64_BLUE
from video2ascii.web.app import JobStatus, app, jobs

client = TestClient(app)


class TestWebApp:
    """Tests for web app endpoints."""

    def setup_method(self):
        """Clear jobs before each test."""
        jobs.clear()

    def test_index_route(self):
        """Test that index route serves HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "video2ascii" in response.text.lower()

    def test_convert_endpoint_missing_file(self):
        """Test convert endpoint without file."""
        response = client.post("/api/convert")
        assert response.status_code != 200

    def test_convert_endpoint_invalid_width(self):
        """Test convert endpoint with invalid width."""
        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {"width": 10}  # Too small
        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 400

    def test_convert_endpoint_invalid_fps(self):
        """Test convert endpoint with invalid fps."""
        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {"fps": 0}  # Too small
        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 400

    def test_convert_endpoint_invalid_charset(self):
        """Test convert endpoint with invalid charset."""
        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {"charset": "invalid_charset_that_does_not_exist"}
        response = client.post("/api/convert", files=files, data=data)
        data["charset"] = "x"  # Too short
        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 400

    @patch("video2ascii.web.app.check_ffmpeg")
    @patch("video2ascii.web.app.extract_frames")
    @patch("video2ascii.web.app.convert_all")
    def test_convert_endpoint_success(
        self, mock_convert_all, mock_extract_frames, mock_check_ffmpeg
    ):
        """Test successful conversion."""
        mock_check_ffmpeg.return_value = None
        mock_extract_frames.return_value = [
            Path("/tmp/frame_000001.png"),
            Path("/tmp/frame_000002.png"),
        ]
        mock_convert_all.return_value = ["Frame 1", "Frame 2"]

        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {
            "width": 160,
            "fps": 12,
            "color": False,
            "invert": False,
            "edge": False,
            "edge_threshold": 0.15,
            "aspect_ratio": 1.2,
            "charset": "classic",
            "crt": False,
        }

        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert "job_id" in result
        assert result["job_id"] in jobs

    def test_get_job_status_not_found(self):
        """Test getting status for non-existent job."""
        response = client.get("/api/jobs/nonexistent/status")
        assert response.status_code == 404

    def test_get_job_status_success(self):
        """Test getting status for existing job."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.PENDING,
            "progress": {"stage": "pending", "current": 0, "total": 0},
            "error": None,
        }

        response = client.get(f"/api/jobs/{job_id}/status")
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == JobStatus.PENDING

    def test_get_frames_not_found(self):
        """Test getting frames for non-existent job."""
        response = client.get("/api/jobs/nonexistent/frames")
        assert response.status_code == 404

    def test_get_frames_not_completed(self):
        """Test getting frames for job that's not completed."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.PENDING,
            "frames": None,
            "params": {"crt_filter": False},
        }

        response = client.get(f"/api/jobs/{job_id}/frames")
        assert response.status_code == 400

    def test_get_frames_success(self):
        """Test getting frames for completed job."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "frames": ["Frame 1", "Frame 2"],
            "color_scheme": None,
            "params": {"fps": 12},
        }

        response = client.get(f"/api/jobs/{job_id}/frames")
        assert response.status_code == 200
        result = response.json()
        assert "frames" in result
        assert len(result["frames"]) == 2

    def test_get_frame_success(self):
        """Test getting a single frame."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "frames": ["Frame 0", "Frame 1", "Frame 2"],
            "color_scheme": None,
            "params": {},
        }

        response = client.get(f"/api/jobs/{job_id}/frame/1")
        assert response.status_code == 200
        result = response.json()
        assert "frame" in result
        assert "Frame 1" in result["frame"]

    def test_get_frame_out_of_range(self):
        """Test getting frame with invalid index."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "frames": ["Frame 0"],
            "color_scheme": None,
            "params": {},
        }

        response = client.get(f"/api/jobs/{job_id}/frame/10")
        assert response.status_code == 404

    def test_delete_job_success(self):
        """Test deleting a job."""
        job_id = "test-job-id"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "work_dir": Path("/tmp/test"),
            "frames": ["Frame 1"],
        }

        response = client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert job_id not in jobs

    def test_delete_job_not_found(self):
        """Test deleting non-existent job."""
        response = client.delete("/api/jobs/nonexistent")
        assert response.status_code == 404

    @patch("video2ascii.web.app.export")
    def test_export_sh_uses_default_crt_playback(self, mock_export, temp_work_dir):
        """Test .sh export uses default_crt_playback, not crt_filter."""
        job_id = "test-export-sh"
        work_dir = temp_work_dir

        def _fake_export(_frames, output_path, _fps, _default_crt_playback):
            output_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

        mock_export.side_effect = _fake_export

        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "work_dir": work_dir,
            "frames": ["Frame 1"],
            "params": {
                "fps": 12,
                "crt_filter": True,
                "default_crt_playback": False,
            },
        }

        response = client.get(f"/api/jobs/{job_id}/export/sh")
        assert response.status_code == 200
        mock_export.assert_called_once()
        assert mock_export.call_args[0][3] is False

    @patch("video2ascii.web.app.check_ffmpeg")
    @patch("video2ascii.web.app.extract_frames")
    @patch("video2ascii.web.app.convert_all")
    def test_convert_with_subtitle_param(
        self, mock_convert_all, mock_extract_frames, mock_check_ffmpeg
    ):
        """Test convert endpoint accepts subtitle=True."""
        mock_check_ffmpeg.return_value = None
        mock_extract_frames.return_value = [Path("/tmp/frame_000001.png")]
        mock_convert_all.return_value = ["Frame 1"]

        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {
            "width": 160,
            "fps": 12,
            "color": False,
            "invert": False,
            "edge": False,
            "edge_threshold": 0.15,
            "aspect_ratio": 1.2,
            "charset": "classic",
            "crt": False,
            "subtitle": True,
        }

        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert "job_id" in result
        job_id = result["job_id"]
        assert jobs[job_id]["params"]["subtitle"] is True

    def test_get_frames_includes_subtitle_segments(self):
        """Test frames response includes subtitle_segments when available."""
        job_id = "test-job-with-subs"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "frames": ["Frame 1", "Frame 2"],
            "subtitle_segments": [(0.0, 2.0, "Hello"), (2.0, 4.0, "World")],
            "color_scheme": None,
            "params": {"fps": 12},
        }

        response = client.get(f"/api/jobs/{job_id}/frames")
        assert response.status_code == 200
        result = response.json()
        assert "subtitle_segments" in result
        assert len(result["subtitle_segments"]) == 2
        assert result["subtitle_segments"][0]["text"] == "Hello"
        assert result["subtitle_segments"][0]["start"] == 0.0
        assert result["subtitle_segments"][0]["end"] == 2.0

    def test_get_frames_no_subtitles(self):
        """Test frames response omits subtitle_segments when None."""
        job_id = "test-job-no-subs"
        jobs[job_id] = {
            "status": JobStatus.COMPLETED,
            "frames": ["Frame 1"],
            "subtitle_segments": None,
            "color_scheme": None,
            "params": {"fps": 12},
        }

        response = client.get(f"/api/jobs/{job_id}/frames")
        assert response.status_code == 200
        result = response.json()
        assert "subtitle_segments" not in result

    def test_fonts_endpoint_petscii(self):
        """Test /api/fonts returns font list for petscii."""
        with patch("video2ascii.web.app.list_available_fonts", return_value=["PetMe64", "PetMe128"]):
            response = client.get("/api/fonts?charset=petscii")
        assert response.status_code == 200
        result = response.json()
        assert "fonts" in result
        assert "PetMe64" in result["fonts"]

    def test_fonts_endpoint_classic_empty(self):
        """Test /api/fonts returns empty list for non-petscii charsets."""
        with patch("video2ascii.web.app.list_available_fonts", return_value=[]):
            response = client.get("/api/fonts?charset=classic")
        assert response.status_code == 200
        result = response.json()
        assert result["fonts"] == []

    @patch("video2ascii.web.app.check_ffmpeg")
    @patch("video2ascii.web.app.extract_frames")
    @patch("video2ascii.web.app.convert_all")
    def test_convert_with_font_param(
        self, mock_convert_all, mock_extract_frames, mock_check_ffmpeg
    ):
        """Test convert endpoint accepts font parameter."""
        mock_check_ffmpeg.return_value = None
        mock_extract_frames.return_value = [Path("/tmp/frame_000001.png")]
        mock_convert_all.return_value = ["Frame 1"]

        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {
            "width": 160,
            "fps": 12,
            "color": False,
            "invert": False,
            "edge": False,
            "edge_threshold": 0.15,
            "aspect_ratio": 1.2,
            "charset": "petscii",
            "crt": False,
            "subtitle": False,
            "font": "PetMe128",
        }

        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        job_id = result["job_id"]
        assert jobs[job_id]["params"]["font"] == "PetMe128"


class TestPresetsEndpoint:
    """Tests for /api/presets endpoint."""

    def test_presets_returns_all(self):
        """Test /api/presets returns all preset names."""
        response = client.get("/api/presets")
        assert response.status_code == 200
        result = response.json()
        assert "classic" in result
        assert "crt" in result
        assert "c64" in result
        assert "sketch" in result
        assert "minimal" in result

    def test_presets_crt_has_color_scheme(self):
        """Test CRT preset includes serialized color_scheme."""
        response = client.get("/api/presets")
        result = response.json()
        crt = result["crt"]
        assert "color_scheme" in crt
        assert crt["color_scheme"]["tint"] == [51, 255, 51]
        assert crt["color_scheme"]["bg"] == [5, 5, 5]

    def test_presets_c64_has_color_scheme(self):
        """Test C64 preset includes serialized color_scheme."""
        response = client.get("/api/presets")
        result = response.json()
        c64 = result["c64"]
        assert "color_scheme" in c64
        assert c64["color_scheme"]["tint"] == [124, 112, 218]
        assert c64["charset"] == "petscii"

    def test_presets_classic_no_color_scheme(self):
        """Test classic preset has no color_scheme."""
        response = client.get("/api/presets")
        result = response.json()
        assert "color_scheme" not in result["classic"]

    @patch("video2ascii.web.app.check_ffmpeg")
    @patch("video2ascii.web.app.extract_frames")
    @patch("video2ascii.web.app.convert_all")
    def test_convert_with_preset_param(
        self, mock_convert_all, mock_extract_frames, mock_check_ffmpeg
    ):
        """Test convert endpoint accepts preset parameter and stores color_scheme."""
        mock_check_ffmpeg.return_value = None
        mock_extract_frames.return_value = [Path("/tmp/frame_000001.png")]
        mock_convert_all.return_value = ["Frame 1"]

        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {
            "width": 40,
            "fps": 12,
            "color": True,
            "invert": False,
            "edge": False,
            "charset": "petscii",
            "crt": False,
            "preset": "c64",
        }

        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        job_id = result["job_id"]
        assert jobs[job_id]["color_scheme"] is C64_BLUE
        assert jobs[job_id]["params"]["preset"] == "c64"

    @patch("video2ascii.web.app.check_ffmpeg")
    @patch("video2ascii.web.app.extract_frames")
    @patch("video2ascii.web.app.convert_all")
    def test_convert_with_preset_only_uses_server_defaults(
        self, mock_convert_all, mock_extract_frames, mock_check_ffmpeg
    ):
        """Test preset-only requests resolve full defaults server-side."""
        mock_check_ffmpeg.return_value = None
        mock_extract_frames.return_value = [Path("/tmp/frame_000001.png")]
        mock_convert_all.return_value = ["Frame 1"]

        files = {"file": ("test.mp4", b"fake video data", "video/mp4")}
        data = {"preset": "c64"}

        response = client.post("/api/convert", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        job_id = result["job_id"]

        params = jobs[job_id]["params"]
        assert params["preset"] == "c64"
        assert params["width"] == 40
        assert params["fps"] == 12
        assert params["charset"] == "petscii"
        assert params["color"] is True
        assert params["invert"] is False
        assert params["edge"] is False
        assert params["crt_filter"] is True
        assert params["default_crt_playback"] is False
