"""FastAPI web application for video2ascii."""

import asyncio
import json
import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from video2ascii.converter import check_ffmpeg, extract_frames, convert_all, CHARSETS
from video2ascii.exporter import export
from video2ascii.fonts import list_available_fonts
from video2ascii.mp4_exporter import export_mp4
from video2ascii.presets import PRESETS, serialize_presets
from video2ascii.subtitle import generate_srt, parse_srt
from video2ascii.web.renderer import frames_to_html

logger = logging.getLogger(__name__)

app = FastAPI(title="video2ascii Web GUI")

# Mount static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Job management
class JobStatus:
    """Job status tracking."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CONVERTING = "converting"
    COMPLETED = "completed"
    ERROR = "error"


jobs: dict[str, dict] = {}


async def _process_video_async(
    job_id: str,
    video_path: Path,
    work_dir: Path,
    width: int,
    fps: int,
    color: bool,
    invert: bool,
    edge: bool,
    edge_threshold: float,
    aspect_ratio: float,
    charset: str,
    crt_filter: bool,
    subtitle: bool = False,
) -> None:
    """
    Asynchronous video processing function.

    Updates job status in the jobs dict as it progresses.
    """
    try:
        jobs[job_id]["status"] = JobStatus.EXTRACTING
        jobs[job_id]["progress"] = {"stage": "extracting", "current": 0, "total": 0}

        loop = asyncio.get_event_loop()
        frame_paths = await loop.run_in_executor(
            None,
            extract_frames,
            video_path,
            fps,
            width,
            work_dir,
            crt_filter,
        )

        jobs[job_id]["status"] = JobStatus.CONVERTING
        jobs[job_id]["progress"] = {"stage": "converting", "current": 0, "total": len(frame_paths)}

        frames = await loop.run_in_executor(
            None,
            convert_all,
            frame_paths,
            width,
            color,
            invert,
            edge,
            aspect_ratio,
            edge_threshold,
            charset,
        )

        subtitle_segments = None
        subtitle_srt_path = None
        if subtitle:
            jobs[job_id]["progress"] = {"stage": "generating subtitles", "current": 0, "total": 0}
            subtitle_srt_path = await loop.run_in_executor(
                None, generate_srt, video_path, work_dir,
            )
            if subtitle_srt_path:
                subtitle_segments = parse_srt(subtitle_srt_path)
                logger.info("Generated %d subtitle segments", len(subtitle_segments))

        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["frames"] = frames
        jobs[job_id]["subtitle_segments"] = subtitle_segments
        jobs[job_id]["subtitle_srt_path"] = subtitle_srt_path
        jobs[job_id]["progress"] = {"stage": "completed", "current": len(frames), "total": len(frames)}

    except Exception as e:
        error_msg = str(e)
        logger.exception(f"Error processing video for job {job_id}: {error_msg}")
        jobs[job_id]["status"] = JobStatus.ERROR
        jobs[job_id]["error"] = error_msg


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main HTML page."""
    index_path = static_dir / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/presets")
async def get_presets():
    """Return all preset definitions (with color schemes serialized)."""
    return serialize_presets()


@app.get("/api/fonts")
async def get_fonts(charset: str = "classic"):
    """Return font names available for a given charset."""
    return {"fonts": list_available_fonts(charset)}


@app.post("/api/convert")
async def convert_video(
    file: UploadFile = File(...),
    width: Optional[int] = Form(None),
    fps: Optional[int] = Form(None),
    color: Optional[bool] = Form(None),
    invert: Optional[bool] = Form(None),
    edge: Optional[bool] = Form(None),
    edge_threshold: float = Form(0.15),
    aspect_ratio: float = Form(1.2),
    charset: Optional[str] = Form(None),
    crt: Optional[bool] = Form(None),
    subtitle: bool = Form(False),
    font: str = Form(""),
    preset: str = Form(""),
):
    """Upload video and start conversion job."""
    preset_def = PRESETS.get(preset, {}) if preset else {}
    width = width if width is not None else preset_def.get("width", 160)
    fps = fps if fps is not None else preset_def.get("fps", 12)
    color = color if color is not None else preset_def.get("color", False)
    invert = invert if invert is not None else preset_def.get("invert", False)
    edge = edge if edge is not None else preset_def.get("edge", False)
    charset = charset if charset is not None else preset_def.get("charset", "classic")

    color_scheme = preset_def.get("color_scheme")
    crt_filter = crt if crt is not None else preset_def.get("crt_filter", False)
    default_crt_playback = crt if crt is not None else preset == "crt"

    logger.info(
        "Convert request: width=%s, fps=%s, charset=%s, color=%s, invert=%s, "
        "preset=%s, crt_filter=%s, default_crt_playback=%s, edge=%s, subtitle=%s, font=%s",
        width, fps, charset, color, invert, preset, crt_filter, default_crt_playback,
        edge, subtitle, font,
    )
    
    if width < 20 or width > 320:
        raise HTTPException(status_code=400, detail="width must be between 20 and 320")
    if fps < 1 or fps > 30:
        raise HTTPException(status_code=400, detail="fps must be between 1 and 30")
    if charset not in CHARSETS and len(charset) < 2:
        raise HTTPException(status_code=400, detail=f"charset must be one of {list(CHARSETS.keys())} or a custom string")

    try:
        check_ffmpeg()
    except SystemExit:
        raise HTTPException(status_code=500, detail="ffmpeg not found. Please install ffmpeg.")

    job_id = str(uuid.uuid4())

    base_name = Path(file.filename).stem if file.filename else "video"
    work_dir = Path(tempfile.mkdtemp(prefix=f"ascii_{base_name}_"))

    video_path = work_dir / "input_video"
    with open(video_path, "wb") as f:
        content = await file.read()
        f.write(content)

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "work_dir": work_dir,
        "video_path": video_path,
        "params": {
            "width": width,
            "fps": fps,
            "color": color,
            "invert": invert,
            "edge": edge,
            "edge_threshold": edge_threshold,
            "aspect_ratio": aspect_ratio,
            "charset": charset,
            "crt_filter": crt_filter,
            "default_crt_playback": default_crt_playback,
            "subtitle": subtitle,
            "font": font or None,
            "preset": preset or None,
        },
        "color_scheme": color_scheme,
        "frames": None,
        "subtitle_segments": None,
        "subtitle_srt_path": None,
        "error": None,
        "progress": {"stage": "pending", "current": 0, "total": 0},
    }

    asyncio.create_task(
        _process_video_async(
            job_id,
            video_path,
            work_dir,
            width,
            fps,
            color,
            invert,
            edge,
            edge_threshold,
            aspect_ratio,
            charset,
            crt_filter,
            subtitle=subtitle,
        )
    )

    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Get job status and progress."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return {
        "status": job["status"],
        "progress": job["progress"],
        "error": job.get("error"),
    }


@app.get("/api/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str):
    """Stream job progress via Server-Sent Events."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        """Generate SSE events."""
        last_status = None
        while True:
            if job_id not in jobs:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break

            job = jobs[job_id]
            status = job["status"]
            progress = job["progress"]

            if status != last_status or progress.get("current", 0) % 10 == 0:
                data = {
                    "status": status,
                    "progress": progress,
                    "error": job.get("error"),
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_status = status

            if status in (JobStatus.COMPLETED, JobStatus.ERROR):
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/jobs/{job_id}/frames")
async def get_frames(job_id: str):
    """Get all converted frames as HTML."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        status = job["status"]
        raise HTTPException(status_code=400, detail=f"Job not completed (status: {status})")

    if job["frames"] is None:
        raise HTTPException(status_code=500, detail="Frames not available")

    color_scheme = job.get("color_scheme")
    html_frames = frames_to_html(job["frames"], color_scheme=color_scheme)

    response = {"frames": html_frames, "fps": job["params"]["fps"]}

    subtitle_segments = job.get("subtitle_segments")
    if subtitle_segments:
        response["subtitle_segments"] = [
            {"start": start, "end": end, "text": text}
            for start, end, text in subtitle_segments
        ]

    return response


@app.get("/api/jobs/{job_id}/frame/{frame_num}")
async def get_frame(job_id: str, frame_num: int):
    """Get a single frame by number."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        status = job["status"]
        raise HTTPException(status_code=400, detail=f"Job not completed (status: {status})")

    if job["frames"] is None:
        raise HTTPException(status_code=500, detail="Frames not available")

    if frame_num < 0 or frame_num >= len(job["frames"]):
        raise HTTPException(status_code=404, detail="Frame number out of range")

    color_scheme = job.get("color_scheme")
    html_frame = frames_to_html([job["frames"][frame_num]], color_scheme=color_scheme)[0]

    return {"frame": html_frame}


@app.get("/api/jobs/{job_id}/export/sh")
async def export_sh(job_id: str):
    """Export as standalone bash script."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        status = job["status"]
        raise HTTPException(status_code=400, detail=f"Job not completed (status: {status})")

    if job["frames"] is None:
        raise HTTPException(status_code=500, detail="Frames not available")

    export_path = job["work_dir"] / "export.sh"
    export(
        job["frames"],
        export_path,
        job["params"]["fps"],
        job["params"]["default_crt_playback"],
    )

    return FileResponse(
        str(export_path),
        media_type="application/x-sh",
        filename="video2ascii.sh",
    )


@app.get("/api/jobs/{job_id}/export/mp4")
async def export_mp4_endpoint(job_id: str):
    """Export as MP4 video."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        status = job["status"]
        raise HTTPException(status_code=400, detail=f"Job not completed (status: {status})")

    if job["frames"] is None:
        raise HTTPException(status_code=500, detail="Frames not available")

    export_path = job["work_dir"] / "export.mp4"
    target_width = min(1920, max(1280, job["params"]["width"] * 16))

    color_scheme = job.get("color_scheme")

    export_mp4(
        job["frames"],
        export_path,
        job["params"]["fps"],
        color=job["params"]["color"],
        color_scheme=color_scheme,
        work_dir=job["work_dir"],
        charset=job["params"]["charset"],
        target_width=target_width,
        codec="h265",
        subtitle_path=job.get("subtitle_srt_path"),
        font_override=job["params"].get("font"),
    )

    return FileResponse(
        str(export_path),
        media_type="video/mp4",
        filename="video2ascii.mp4",
    )


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete job and clean up files."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    work_dir = job["work_dir"]

    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    del jobs[job_id]

    return {"message": "Job deleted"}


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    for job in jobs.values():
        work_dir = job.get("work_dir")
        if work_dir and Path(work_dir).exists():
            shutil.rmtree(work_dir, ignore_errors=True)
