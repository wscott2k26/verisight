from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .analyzer_runtime import DETECTOR, analyze_image_bytes, analyze_video_bytes

MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "25"))
MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "150"))
ANALYSIS_CONCURRENCY = max(1, int(os.getenv("ANALYSIS_CONCURRENCY", "1")))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
STATIC_DIR = Path(
    os.getenv(
        "STATIC_DIR",
        str(Path(__file__).resolve().parents[2] / "dist"),
    )
).resolve()
analysis_slots = asyncio.Semaphore(ANALYSIS_CONCURRENCY)

IMAGE_MIME_PREFIX = "image/"
VIDEO_MIME_PREFIX = "video/"


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(
    title="VeriSight Media Forensics API",
    version="2.2.0",
    description="Probabilistic AI-image, deepfake-video and editing-forensics screening.",
    lifespan=lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=1200)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def security_and_timing(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)

    path = request.url.path
    if path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    elif path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    else:
        response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(int((time.perf_counter() - started) * 1000))
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


async def read_limited(upload: UploadFile, max_mb: int) -> bytes:
    limit = max_mb * 1024 * 1024
    content = await upload.read(limit + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > limit:
        raise HTTPException(status_code=413, detail=f"File exceeds the {max_mb} MB limit.")
    return content


def validate_mime(upload: UploadFile, prefix: str, label: str) -> None:
    content_type = (upload.content_type or "").lower()
    if content_type and not content_type.startswith(prefix):
        raise HTTPException(status_code=415, detail=f"The uploaded file is not a supported {label}.")


@app.get("/api")
async def api_root():
    return {
        "name": "VeriSight Media Forensics API",
        "version": "2.2.0",
        "docs": "/docs",
        "health": "/api/health",
        "notice": "Probabilistic screening is not proof.",
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "version": "2.2.0",
        "model": DETECTOR.info(),
        "frontend": (STATIC_DIR / "index.html").is_file(),
        "limits": {
            "image_mb": MAX_IMAGE_MB,
            "video_mb": MAX_VIDEO_MB,
            "concurrency": ANALYSIS_CONCURRENCY,
        },
    }


@app.post("/api/model/load")
async def load_model():
    loaded = await asyncio.to_thread(DETECTOR.load)
    return {"loaded": loaded, "model": DETECTOR.info()}


@app.post("/api/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    validate_mime(file, IMAGE_MIME_PREFIX, "image")
    content = await read_limited(file, MAX_IMAGE_MB)
    filename = file.filename or "uploaded-image"
    async with analysis_slots:
        try:
            return await asyncio.to_thread(analyze_image_bytes, content, filename)
        except ValueError:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Image analysis failed: {type(exc).__name__}") from exc


@app.post("/api/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    validate_mime(file, VIDEO_MIME_PREFIX, "video")
    content = await read_limited(file, MAX_VIDEO_MB)
    filename = file.filename or "uploaded-video"
    async with analysis_slots:
        try:
            return await asyncio.to_thread(analyze_video_bytes, content, filename)
        except ValueError:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Video analysis failed: {type(exc).__name__}") from exc


assets_dir = STATIC_DIR / "assets"
if assets_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def frontend(full_path: str):
    """Serve Vite's production build while preserving all /api and /docs routes."""
    if full_path.startswith(("api/", "docs", "openapi.json", "redoc")):
        raise HTTPException(status_code=404, detail="Not found")

    if STATIC_DIR.is_dir() and full_path:
        candidate = (STATIC_DIR / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(STATIC_DIR):
            return FileResponse(candidate)

    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return JSONResponse(
        status_code=503,
        content={
            "detail": "The frontend build is unavailable.",
            "api": "/api",
            "health": "/api/health",
        },
    )
