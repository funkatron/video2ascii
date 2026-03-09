"""HTTP API for video exports (WebM/MP4)."""

import base64
import hashlib
import hmac
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, model_validator
from starlette.background import BackgroundTask

from video2ascii.mp4_exporter import export_mp4
from video2ascii.presets import CRT_GREEN

app = FastAPI(title="video2ascii Export API")


def _cors_origins() -> list[str]:
    raw = os.environ.get("VIDEO2ASCII_CORS_ALLOW_ORIGINS", "*")
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ExportRequest(BaseModel):
    frames: list[str] = Field(min_length=1, max_length=1200)
    fps: int = Field(ge=1, le=30)
    width: int = Field(default=120, ge=20, le=320)
    color: bool = False
    crt: bool = False
    charset: str = "classic"
    font: Optional[str] = None

    @model_validator(mode="after")
    def validate_frame_sizes(self) -> "ExportRequest":
        max_chars = int(os.environ.get("VIDEO2ASCII_MAX_CHARS_PER_FRAME", "20000"))
        for frame in self.frames:
            if len(frame) > max_chars:
                raise ValueError(f"Frame exceeds max chars ({max_chars})")
        return self


_RATE_WINDOW_SECONDS = 60
_RATE_LIMIT = int(os.environ.get("VIDEO2ASCII_RATE_LIMIT_PER_MINUTE", "20"))
_RATE_STATE: dict[str, list[float]] = {}


def _check_token(auth_header: Optional[str]) -> None:
    expected = os.environ.get("VIDEO2ASCII_EXPORT_TOKEN", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.replace("Bearer ", "", 1).strip()
    if expected and token == expected:
        return
    if _free_mode_enabled() and _verify_signed_token(token):
        return
    if not expected and not _free_mode_enabled():
        raise HTTPException(status_code=500, detail="Server auth token is not configured")
    raise HTTPException(status_code=403, detail="Invalid token")


def _free_mode_enabled() -> bool:
    return os.environ.get("VIDEO2ASCII_FREE_MODE", "").lower() == "true"


def _verify_signed_token(token: str) -> bool:
    secret = os.environ.get("VIDEO2ASCII_FREE_ISSUER_SECRET", "")
    if not secret:
        return False
    parts = token.split(".")
    if len(parts) != 2:
        return False
    payload_b64, provided_sig = parts
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return False
    try:
        payload_bytes = base64.b64decode(payload_b64 + "===")
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return False
    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return False
    return exp > int(time.time() * 1000)


def _safe_target_width(width_chars: int) -> int:
    return min(1920, max(1280, width_chars * 16))


def _check_rate_limit(request: Request) -> None:
    import time

    if _RATE_LIMIT <= 0:
        return
    now = time.time()
    client_ip = request.client.host if request.client else "unknown"
    hits = _RATE_STATE.get(client_ip, [])
    hits = [t for t in hits if now - t < _RATE_WINDOW_SECONDS]
    if len(hits) >= _RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    hits.append(now)
    _RATE_STATE[client_ip] = hits


def _check_content_length(request: Request) -> None:
    limit_bytes = int(os.environ.get("VIDEO2ASCII_MAX_REQUEST_BYTES", "20000000"))
    raw = request.headers.get("content-length")
    if raw and raw.isdigit() and int(raw) > limit_bytes:
        raise HTTPException(status_code=413, detail="Request too large")


def _run_export(req: ExportRequest, suffix: str, codec: str) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix="video2ascii_export_"))
    out_path = work_dir / f"export{suffix}"
    color_scheme = CRT_GREEN if req.crt else None
    export_mp4(
        req.frames,
        out_path,
        req.fps,
        color=req.color,
        color_scheme=color_scheme,
        work_dir=work_dir,
        charset=req.charset,
        target_width=_safe_target_width(req.width),
        codec=codec,
        font_override=req.font,
    )
    return out_path


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/export/webm")
def export_webm(
    req: ExportRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> FileResponse:
    _check_content_length(request)
    _check_rate_limit(request)
    _check_token(authorization)
    out_path = _run_export(req, ".webm", "vp9")
    cleanup = BackgroundTask(shutil.rmtree, str(out_path.parent), True)
    return FileResponse(
        str(out_path),
        media_type="video/webm",
        filename="video2ascii.webm",
        background=cleanup,
    )


@app.post("/api/export/mp4")
def export_mp4_route(
    req: ExportRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
) -> FileResponse:
    _check_content_length(request)
    _check_rate_limit(request)
    _check_token(authorization)
    out_path = _run_export(req, ".mp4", "h265")
    cleanup = BackgroundTask(shutil.rmtree, str(out_path.parent), True)
    return FileResponse(
        str(out_path),
        media_type="video/mp4",
        filename="video2ascii.mp4",
        background=cleanup,
    )
