"""Tests for deployment mp4/webm export API."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from video2ascii.services.mp4_api import app

client = TestClient(app)


def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("video2ascii.services.mp4_api.export_mp4")
def test_export_webm(mock_export_mp4, monkeypatch):
    monkeypatch.setenv("VIDEO2ASCII_EXPORT_TOKEN", "test-token")
    monkeypatch.delenv("VIDEO2ASCII_ALLOW_UNAUTH", raising=False)
    payload = {
        "frames": ["abc\n123"],
        "fps": 12,
        "width": 120,
        "color": False,
        "crt": False,
        "charset": "classic",
    }

    def create_file(*args, **kwargs):
        out_path: Path = args[1]
        out_path.write_bytes(b"WEBM")

    mock_export_mp4.side_effect = create_file
    response = client.post(
        "/api/export/webm",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/webm")


@patch("video2ascii.services.mp4_api.export_mp4")
def test_export_mp4(mock_export_mp4, monkeypatch):
    monkeypatch.setenv("VIDEO2ASCII_EXPORT_TOKEN", "test-token")
    monkeypatch.delenv("VIDEO2ASCII_ALLOW_UNAUTH", raising=False)
    payload = {
        "frames": ["abc\n123"],
        "fps": 12,
        "width": 120,
    }

    def create_file(*args, **kwargs):
        out_path: Path = args[1]
        out_path.write_bytes(b"MP4")

    mock_export_mp4.side_effect = create_file
    response = client.post(
        "/api/export/mp4",
        json=payload,
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("video/mp4")


def test_export_webm_requires_auth_when_token_configured(monkeypatch):
    monkeypatch.setenv("VIDEO2ASCII_EXPORT_TOKEN", "test-token")
    monkeypatch.delenv("VIDEO2ASCII_ALLOW_UNAUTH", raising=False)
    response = client.post("/api/export/webm", json={"frames": ["x"], "fps": 12, "width": 120})
    assert response.status_code == 401


def test_cors_preflight_export_webm():
    response = client.options(
        "/api/export/webm",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    allow_headers = response.headers.get("access-control-allow-headers", "").lower()
    assert "authorization" in allow_headers
    assert "content-type" in allow_headers


@patch("video2ascii.services.mp4_api.export_mp4")
def test_cors_simple_response_export_mp4(mock_export_mp4, monkeypatch):
    monkeypatch.setenv("VIDEO2ASCII_EXPORT_TOKEN", "test-token")

    def create_file(*args, **kwargs):
        out_path: Path = args[1]
        out_path.write_bytes(b"MP4")

    mock_export_mp4.side_effect = create_file
    response = client.post(
        "/api/export/mp4",
        json={"frames": ["x"], "fps": 12, "width": 120},
        headers={"Origin": "https://example.com", "Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
