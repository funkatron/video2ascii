"""Tests for deployment mp4/webm export API."""

import base64
import hashlib
import hmac
import json
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from video2ascii.services.mp4_api import app

client = TestClient(app)


def _signed_free_token(secret: str, ttl_seconds: int = 3600) -> str:
    payload = {
        "tier": "free",
        "iat": int(time.time() * 1000),
        "exp": int(time.time() * 1000) + (ttl_seconds * 1000),
        "sid": "test-free-token",
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{signature}"


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


def test_export_webm_requires_auth_in_free_mode(monkeypatch):
    monkeypatch.delenv("VIDEO2ASCII_EXPORT_TOKEN", raising=False)
    monkeypatch.setenv("VIDEO2ASCII_FREE_MODE", "true")
    monkeypatch.setenv("VIDEO2ASCII_FREE_ISSUER_SECRET", "free-secret")
    response = client.post("/api/export/webm", json={"frames": ["x"], "fps": 12, "width": 120})
    assert response.status_code == 401


@patch("video2ascii.services.mp4_api.export_mp4")
def test_export_webm_accepts_signed_free_token(mock_export_mp4, monkeypatch):
    monkeypatch.delenv("VIDEO2ASCII_EXPORT_TOKEN", raising=False)
    monkeypatch.setenv("VIDEO2ASCII_FREE_MODE", "true")
    monkeypatch.setenv("VIDEO2ASCII_FREE_ISSUER_SECRET", "free-secret")

    def create_file(*args, **kwargs):
        out_path: Path = args[1]
        out_path.write_bytes(b"WEBM")

    mock_export_mp4.side_effect = create_file
    token = _signed_free_token("free-secret")
    response = client.post(
        "/api/export/webm",
        json={"frames": ["x"], "fps": 12, "width": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


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
