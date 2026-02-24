"""HTTP API for paid video exports (WebM/MP4)."""

import os
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from video2ascii.mp4_exporter import export_mp4

app = FastAPI(title="video2ascii Export API")


class ExportRequest(BaseModel):
    frames: list[str] = Field(min_length=1)
    fps: int = Field(ge=1, le=30)
    width: int = Field(default=120, ge=20, le=320)
    color: bool = False
    crt: bool = False
    charset: str = "classic"
    font: Optional[str] = None


def _check_token(auth_header: Optional[str]) -> None:
    expected = os.environ.get("VIDEO2ASCII_EXPORT_TOKEN", "")
    if not expected:
        # Allow disabled auth in development.
        return
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = auth_header.replace("Bearer ", "", 1).strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid token")


def _safe_target_width(width_chars: int) -> int:
    return min(1920, max(1280, width_chars * 16))


def _run_export(req: ExportRequest, suffix: str, codec: str) -> Path:
    work_dir = Path(tempfile.mkdtemp(prefix="video2ascii_export_"))
    out_path = work_dir / f"export{suffix}"
    export_mp4(
        req.frames,
        out_path,
        req.fps,
        color=req.color,
        crt=req.crt,
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
def export_webm(req: ExportRequest, authorization: Optional[str] = Header(default=None)) -> FileResponse:
    _check_token(authorization)
    out_path = _run_export(req, ".webm", "vp9")
    return FileResponse(str(out_path), media_type="video/webm", filename="video2ascii.webm")


@app.post("/api/export/mp4")
def export_mp4_route(req: ExportRequest, authorization: Optional[str] = Header(default=None)) -> FileResponse:
    _check_token(authorization)
    out_path = _run_export(req, ".mp4", "h265")
    return FileResponse(str(out_path), media_type="video/mp4", filename="video2ascii.mp4")
