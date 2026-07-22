from __future__ import annotations

import base64
import io
import math
import os
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFile, ImageOps

ImageFile.LOAD_TRUNCATED_IMAGES = True

MODEL_ID = os.getenv("DETECTOR_MODEL", "prithivMLmods/deepfake-detector-model-v1")
ENABLE_ML = os.getenv("ENABLE_ML", "true").lower() not in {"0", "false", "no", "off"}
MAX_ANALYSIS_DIM = int(os.getenv("MAX_ANALYSIS_DIM", "1280"))
MAX_VIDEO_ANALYSIS_DIM = int(os.getenv("MAX_VIDEO_ANALYSIS_DIM", "900"))
MAX_VIDEO_FRAMES = int(os.getenv("MAX_VIDEO_FRAMES", "14"))
VIDEO_SAMPLE_SECONDS = float(os.getenv("VIDEO_SAMPLE_SECONDS", "2.5"))
MODEL_VIDEO_FRAMES = int(os.getenv("MODEL_VIDEO_FRAMES", "6"))


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def rounded(value: float) -> int:
    return int(round(clamp(value)))


def data_url(image: Image.Image, fmt: str = "JPEG", quality: int = 78) -> str:
    buffer = io.BytesIO()
    save_image = image.convert("RGB")
    kwargs = {"quality": quality, "optimize": True} if fmt.upper() == "JPEG" else {}
    save_image.save(buffer, format=fmt, **kwargs)
    mime = "image/jpeg" if fmt.upper() == "JPEG" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(buffer.getvalue()).decode('ascii')}"


def resize_image(image: Image.Image, max_dim: int) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    if max(image.size) <= max_dim:
        return image
    copy = image.copy()
    copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
    return copy


def cv_rgb(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("RGB"), dtype=np.uint8)


def safe_percentile(values: np.ndarray, percentile: float) -> float:
    if values.size == 0:
        return 0.0
    return float(np.percentile(values, percentile))


class LazyDetector:
    def __init__(self) -> None:
        self.status = "disabled" if not ENABLE_ML else "not_loaded"
        self.error: str | None = None
        self._processor = None
        self._model = None
        self._torch = None
        self._lock = threading.Lock()

    def info(self) -> dict[str, Any]:
        return {
            "id": MODEL_ID,
            "status": self.status,
            "error": self.error,
            "enabled": ENABLE_ML,
        }

    def load(self) -> bool:
        if not ENABLE_ML:
            self.status = "disabled"
            return False
        if self.status == "ready":
            return True
        if self.status == "failed":
            return False
        with self._lock:
            if self.status == "ready":
                return True
            self.status = "loading"
            try:
                import torch
                from transformers import AutoImageProcessor, AutoModelForImageClassification

                self._processor = AutoImageProcessor.from_pretrained(MODEL_ID)
                self._model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
                self._model.eval()
                self._torch = torch
                self.status = "ready"
                self.error = None
                return True
            except Exception as exc:  # network/model errors must not fake a neural result
                self.status = "failed"
                self.error = f"{type(exc).__name__}: {exc}"[:500]
                self._processor = None
                self._model = None
                self._torch = None
                return False

    def predict_fake_probability(self, image: Image.Image) -> float | None:
        if not self.load():
            return None
        try:
            inputs = self._processor(images=image.convert("RGB"), return_tensors="pt")
            with self._torch.no_grad():
                logits = self._model(**inputs).logits[0]
                probabilities = self._torch.softmax(logits, dim=-1).cpu().numpy()
            id2label = getattr(self._model.config, "id2label", {}) or {}
            fake_probability = None
            for index, probability in enumerate(probabilities):
                label = str(id2label.get(index, index)).lower()
                if any(word in label for word in ("fake", "synthetic", "generated", "ai")):
                    fake_probability = float(probability)
                    break
            if fake_probability is None:
                if len(probabilities) == 2:
                    labels = [str(id2label.get(i, i)).lower() for i in range(2)]
                    real_index = next((i for i, label in enumerate(labels) if "real" in label or "authentic" in label), None)
                    fake_probability = 1.0 - float(probabilities[real_index]) if real_index is not None else float(probabilities[-1])
                else:
                    fake_probability = float(np.max(probabilities))
            return clamp(fake_probability * 100.0)
        except Exception as exc:
            self.error = f"Prediction error: {type(exc).__name__}: {exc}"[:500]
            return None


DETECTOR = LazyDetector()

try:
    FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except Exception:
    FACE_CASCADE = None


@dataclass
class ImageFeatures:
    width: int
    height: int
    entropy: float
    laplacian: float
    edge_density: float
    noise_std: float
    saturation_mean: float
    saturation_std: float
    blockiness: float
    high_frequency_ratio: float
    ela_mean: float
    ela_p95: float
    face_count: int
    face_smoothness: float
    metadata_count: int


def entropy_score(gray: np.ndarray) -> float:
    histogram = cv2.calcHist([gray], [0], None, [256], [0, 256]).ravel()
    probabilities = histogram / max(histogram.sum(), 1.0)
    probabilities = probabilities[probabilities > 0]
    return float(-(probabilities * np.log2(probabilities)).sum())


def blockiness_score(gray: np.ndarray) -> float:
    if gray.shape[0] < 18 or gray.shape[1] < 18:
        return 0.0
    vertical_boundary = np.abs(gray[:, 8::8].astype(np.float32) - gray[:, 7::8].astype(np.float32)).mean()
    horizontal_boundary = np.abs(gray[8::8, :].astype(np.float32) - gray[7::8, :].astype(np.float32)).mean()
    vertical_regular = np.abs(gray[:, 5::8].astype(np.float32) - gray[:, 4::8].astype(np.float32)).mean()
    horizontal_regular = np.abs(gray[5::8, :].astype(np.float32) - gray[4::8, :].astype(np.float32)).mean()
    return max(0.0, float((vertical_boundary + horizontal_boundary) - (vertical_regular + horizontal_regular)))


def frequency_ratio(gray: np.ndarray) -> float:
    sample = cv2.resize(gray, (min(512, gray.shape[1]), min(512, gray.shape[0])), interpolation=cv2.INTER_AREA)
    spectrum = np.abs(np.fft.fftshift(np.fft.fft2(sample.astype(np.float32))))
    h, w = spectrum.shape
    yy, xx = np.ogrid[:h, :w]
    distance = np.sqrt((yy - h / 2) ** 2 + (xx - w / 2) ** 2)
    threshold = min(h, w) * 0.24
    high = spectrum[distance >= threshold].sum()
    total = spectrum.sum() + 1e-6
    return float(high / total)


def face_metrics(rgb: np.ndarray, gray: np.ndarray) -> tuple[int, float, list[tuple[int, int, int, int]]]:
    if FACE_CASCADE is None or FACE_CASCADE.empty():
        return 0, 0.0, []
    min_side = max(36, int(min(gray.shape[:2]) * 0.08))
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.12, minNeighbors=5, minSize=(min_side, min_side))
    smooth_values: list[float] = []
    face_list: list[tuple[int, int, int, int]] = []
    for x, y, w, h in faces[:6]:
        face = rgb[y:y + h, x:x + w]
        face_gray = gray[y:y + h, x:x + w]
        if face.size == 0:
            continue
        residual = face.astype(np.float32) - cv2.GaussianBlur(face, (0, 0), 1.4).astype(np.float32)
        texture = float(np.std(residual))
        edge = float((cv2.Canny(face_gray, 55, 135) > 0).mean())
        smooth = clamp((10.5 - texture) * 7.2 + (0.075 - edge) * 310.0)
        smooth_values.append(smooth)
        face_list.append((int(x), int(y), int(w), int(h)))
    return len(face_list), float(np.mean(smooth_values)) if smooth_values else 0.0, face_list


def ela_map(image: Image.Image) -> tuple[Image.Image, float, float, np.ndarray]:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=86, optimize=True)
    buffer.seek(0)
    recompressed = Image.open(buffer).convert("RGB")
    difference = ImageChops.difference(image.convert("RGB"), recompressed)
    diff_array = np.asarray(difference, dtype=np.float32)
    magnitude = np.mean(diff_array, axis=2)
    p99 = safe_percentile(magnitude, 99.0)
    scale = 255.0 / max(p99, 1.0)
    normalized = np.clip(magnitude * scale, 0, 255).astype(np.uint8)
    colored = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
    colored = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    overlay = cv2.addWeighted(np.asarray(image), 0.48, colored, 0.66, 0)
    return Image.fromarray(overlay), float(magnitude.mean()), safe_percentile(magnitude, 95.0), magnitude


def collect_features(image: Image.Image, metadata_count: int) -> tuple[ImageFeatures, Image.Image, list[tuple[int, int, int, int]], np.ndarray]:
    rgb = cv_rgb(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    laplacian = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    edges = cv2.Canny(gray, 55, 135)
    edge_density = float((edges > 0).mean())
    residual = gray.astype(np.float32) - cv2.GaussianBlur(gray, (0, 0), 1.25).astype(np.float32)
    noise_std = float(np.std(residual))
    face_count, face_smoothness, faces = face_metrics(rgb, gray)
    evidence, ela_mean, ela_p95, magnitude = ela_map(image)
    features = ImageFeatures(
        width=image.width,
        height=image.height,
        entropy=entropy_score(gray),
        laplacian=laplacian,
        edge_density=edge_density,
        noise_std=noise_std,
        saturation_mean=float(hsv[:, :, 1].mean()),
        saturation_std=float(hsv[:, :, 1].std()),
        blockiness=blockiness_score(gray),
        high_frequency_ratio=frequency_ratio(gray),
        ela_mean=ela_mean,
        ela_p95=ela_p95,
        face_count=face_count,
        face_smoothness=face_smoothness,
        metadata_count=metadata_count,
    )
    return features, evidence, faces, magnitude


def score_features(features: ImageFeatures, magnitude: np.ndarray, faces: list[tuple[int, int, int, int]]) -> dict[str, float]:
    smooth_global = clamp((9.5 - features.noise_std) * 7.0 + (0.055 - features.edge_density) * 260.0)
    low_entropy = clamp((7.0 - features.entropy) * 24.0)
    frequency_anomaly = clamp((features.high_frequency_ratio - 0.075) * 1150.0)
    block_anomaly = clamp((features.blockiness - 1.2) * 12.0)
    ela_anomaly = clamp((features.ela_p95 - 8.0) * 4.6 + (features.ela_mean - 1.7) * 6.0)
    saturation_anomaly = clamp(abs(features.saturation_mean - 82.0) * 0.72 + max(0.0, 35.0 - features.saturation_std) * 1.0)
    metadata_signal = 18.0 if features.metadata_count == 0 else clamp(12.0 - features.metadata_count * 1.5)

    face_ela = 0.0
    if faces:
        values = []
        for x, y, w, h in faces:
            region = magnitude[y:y + h, x:x + w]
            if region.size:
                values.append(safe_percentile(region, 92.0))
        if values:
            face_ela = clamp((float(np.mean(values)) - 5.0) * 7.0)

    synthetic_heuristic = clamp(
        0.24 * smooth_global
        + 0.20 * frequency_anomaly
        + 0.18 * ela_anomaly
        + 0.14 * low_entropy
        + 0.12 * metadata_signal
        + 0.07 * block_anomaly
        + 0.05 * saturation_anomaly
    )
    deepfake = clamp(
        (0.50 * features.face_smoothness + 0.35 * face_ela + 0.15 * ela_anomaly)
        if features.face_count else 0.30 * ela_anomaly
    )
    filter_probability = clamp(
        0.52 * max(features.face_smoothness, smooth_global)
        + 0.30 * saturation_anomaly
        + 0.18 * low_entropy
    )
    compression = clamp(0.56 * ela_anomaly + 0.44 * block_anomaly)
    return {
        "synthetic_heuristic": synthetic_heuristic,
        "deepfake": deepfake,
        "filter": filter_probability,
        "compression": compression,
        "texture": clamp(0.55 * smooth_global + 0.45 * frequency_anomaly),
        "metadata": metadata_signal,
        "ela": ela_anomaly,
    }


def verdict_for(authenticity: int, synthetic: int, deepfake: int, filters: int) -> tuple[str, str, str]:
    primary = max(synthetic, deepfake)
    if primary >= 70:
        return "high", "Strong synthetic-media indicators", "Multiple signals suggest the media may be AI-generated or facially manipulated."
    if primary >= 45:
        return "mixed", "Mixed or suspicious indicators", "Some signals deserve a closer look, but the scan is not conclusive."
    if filters >= 62:
        return "mixed", "Likely heavily filtered or enhanced", "The media looks more edited than synthetic; authenticity may still be genuine."
    if authenticity >= 72:
        return "low", "Likely authentic", "No strong synthetic or deepfake pattern was found in this screening."
    return "mixed", "Uncertain result", "The available signals do not agree strongly enough for a confident label."


def build_explanation(risk: str, model_used: bool, synthetic: int, deepfake: int, filters: int, confidence: int) -> str:
    mode = "The neural detector and forensic checks" if model_used else "The transparent forensic checks"
    if risk == "high":
        core = f"{mode} found several patterns associated with synthetic or manipulated media."
    elif risk == "low":
        core = f"{mode} did not find a strong synthetic-media pattern in this file."
    else:
        core = f"{mode} found a mixture of normal and unusual signals, so the result should be treated as uncertain."
    return f"{core} Synthetic risk is {synthetic}%, deepfake risk is {deepfake}%, and heavy-filter risk is {filters}%. Confidence is {confidence}%, which measures signal agreement—not absolute truth."


def analyze_pil(
    image: Image.Image,
    filename: str,
    *,
    include_evidence: bool = True,
    include_model: bool = True,
    max_dim: int = MAX_ANALYSIS_DIM,
    metadata_count: int = 0,
) -> dict[str, Any]:
    started = time.perf_counter()
    original_size = image.size
    image = resize_image(image, max_dim)
    features, evidence, faces, magnitude = collect_features(image, metadata_count)
    scored = score_features(features, magnitude, faces)
    model_probability = DETECTOR.predict_fake_probability(image) if include_model else None
    model_used = model_probability is not None
    synthetic = clamp(0.68 * model_probability + 0.32 * scored["synthetic_heuristic"]) if model_used else scored["synthetic_heuristic"]
    deepfake = scored["deepfake"]
    filters = scored["filter"]
    total_risk = clamp(max(synthetic, deepfake * 0.93, filters * 0.48, 0.72 * synthetic + 0.28 * deepfake))
    authenticity = rounded(100.0 - total_risk)
    signal_values = [synthetic, deepfake, filters, scored["ela"], scored["texture"]]
    agreement = 100.0 - min(55.0, float(np.std(signal_values)))
    confidence = rounded((0.72 * agreement + (20.0 if model_used else 4.0)) if model_used else min(72.0, 0.68 * agreement + 10.0))
    synthetic_i, deepfake_i, filters_i = rounded(synthetic), rounded(deepfake), rounded(filters)
    risk, verdict, detail = verdict_for(authenticity, synthetic_i, deepfake_i, filters_i)

    signals = [
        {"name": "Synthetic-generation pattern", "score": synthetic_i, "detail": "Combines neural classification when available with texture, frequency, entropy and recompression evidence."},
        {"name": "Face manipulation", "score": deepfake_i, "detail": f"Checks facial smoothing and local evidence differences across {features.face_count} detected face region(s)." if features.face_count else "No reliable frontal face was found; deepfake confidence is therefore limited."},
        {"name": "Filter and retouching", "score": filters_i, "detail": "Looks for unusually smooth texture, saturation behavior and reduced natural micro-detail."},
        {"name": "Recompression inconsistency", "score": rounded(scored["ela"]), "detail": "Measures how differently local regions respond when the file is recompressed."},
        {"name": "Texture and frequency structure", "score": rounded(scored["texture"]), "detail": "Measures high-frequency structure, edge density and noise consistency."},
        {"name": "Metadata context", "score": rounded(scored["metadata"]), "detail": "Missing metadata is common after social sharing and is only a weak contextual clue."},
    ]
    signals.sort(key=lambda item: item["score"], reverse=True)

    result = {
        "filename": filename,
        "media_type": "image",
        "authenticity_score": authenticity,
        "synthetic_probability": synthetic_i,
        "deepfake_probability": deepfake_i,
        "filter_probability": filters_i,
        "confidence": confidence,
        "risk": risk,
        "verdict": verdict,
        "verdict_detail": detail,
        "explanation": build_explanation(risk, model_used, synthetic_i, deepfake_i, filters_i, confidence),
        "signals": signals,
        "strongest_signals": signals[:3],
        "next_steps": [
            "Compare against the original file or trusted source when possible.",
            "Check provenance, timestamps and context instead of relying on one detector.",
            "For high-stakes use, preserve the original and seek qualified forensic review.",
        ],
        "model": {
            "used": model_used,
            "mode": f"Neural + forensic ({MODEL_ID})" if model_used else "Forensic fallback — neural model unavailable",
            "status": DETECTOR.status,
        },
        "technical": {
            "original_resolution": f"{original_size[0]}×{original_size[1]}",
            "analysis_resolution": f"{image.width}×{image.height}",
            "faces_detected": features.face_count,
            "metadata_fields": metadata_count,
            "entropy": round(features.entropy, 3),
            "noise_std": round(features.noise_std, 3),
            "laplacian_variance": round(features.laplacian, 3),
            "ela_mean": round(features.ela_mean, 3),
            "ela_p95": round(features.ela_p95, 3),
        },
        "processing_ms": int((time.perf_counter() - started) * 1000),
    }
    if include_evidence:
        result["evidence_image"] = data_url(evidence, "JPEG", 80)
    return result


def read_image_bytes(content: bytes) -> tuple[Image.Image, int]:
    try:
        source = Image.open(io.BytesIO(content))
        metadata_count = len(source.getexif() or {})
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.load()
        return image, metadata_count
    except Exception as exc:
        raise ValueError(f"The uploaded file could not be decoded as an image: {exc}") from exc


def analyze_image_bytes(content: bytes, filename: str) -> dict[str, Any]:
    image, metadata_count = read_image_bytes(content)
    return analyze_pil(image, filename, metadata_count=metadata_count)


def frame_thumbnail(frame_rgb: np.ndarray) -> str:
    image = Image.fromarray(frame_rgb)
    image.thumbnail((260, 150), Image.Resampling.LANCZOS)
    return data_url(image, "JPEG", 66)


def analyze_video_bytes(content: bytes, filename: str) -> dict[str, Any]:
    started = time.perf_counter()
    suffix = Path(filename).suffix.lower() or ".mp4"
    temporary_path = None
    capture = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temporary:
            temporary.write(content)
            temporary_path = temporary.name
        capture = cv2.VideoCapture(temporary_path)
        if not capture.isOpened():
            raise ValueError("The video decoder could not open this file or codec.")
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        duration = (frame_count / fps) if fps > 0 and frame_count > 0 else 0.0
        if duration <= 0:
            duration = 1.0
        requested = max(4, int(math.ceil(duration / max(VIDEO_SAMPLE_SECONDS, .5))) + 1)
        sample_count = min(MAX_VIDEO_FRAMES, requested, max(frame_count, 1))
        timestamps = np.linspace(0.0, max(0.0, duration - (1.0 / max(fps, 1.0))), sample_count)
        frames: list[dict[str, Any]] = []
        frame_results: list[dict[str, Any]] = []
        peak_image: Image.Image | None = None
        peak_score = -1.0
        peak_timestamp = 0.0

        for index, timestamp in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000.0)
            ok, frame_bgr = capture.read()
            if not ok or frame_bgr is None:
                continue
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            pil = Image.fromarray(frame_rgb)
            result = analyze_pil(
                pil,
                f"{filename} @ {timestamp:.2f}s",
                include_evidence=False,
                include_model=index < MODEL_VIDEO_FRAMES,
                max_dim=MAX_VIDEO_ANALYSIS_DIM,
                metadata_count=0,
            )
            risk_score = max(result["synthetic_probability"], result["deepfake_probability"])
            frame_results.append(result)
            frames.append({
                "timestamp": round(float(timestamp), 3),
                "score": rounded(risk_score),
                "synthetic": result["synthetic_probability"],
                "deepfake": result["deepfake_probability"],
                "thumbnail": frame_thumbnail(frame_rgb),
            })
            if risk_score > peak_score:
                peak_score = risk_score
                peak_timestamp = float(timestamp)
                peak_image = pil.copy()

        if not frame_results:
            raise ValueError("No decodable video frames were found.")

        synthetic_values = np.array([item["synthetic_probability"] for item in frame_results], dtype=np.float32)
        deepfake_values = np.array([item["deepfake_probability"] for item in frame_results], dtype=np.float32)
        filter_values = np.array([item["filter_probability"] for item in frame_results], dtype=np.float32)
        score_movement = float(np.std(np.maximum(synthetic_values, deepfake_values)))
        temporal_signal = clamp(score_movement * 3.2 + (float(np.max(deepfake_values)) - float(np.median(deepfake_values))) * 1.2)
        synthetic = clamp(0.55 * float(np.median(synthetic_values)) + 0.45 * float(np.max(synthetic_values)))
        deepfake = clamp(0.45 * float(np.median(deepfake_values)) + 0.40 * float(np.max(deepfake_values)) + 0.15 * temporal_signal)
        filters = clamp(0.65 * float(np.median(filter_values)) + 0.35 * float(np.max(filter_values)))
        total_risk = clamp(max(synthetic, deepfake, filters * .42))
        authenticity = rounded(100.0 - total_risk)
        model_used = any(item["model"]["used"] for item in frame_results)
        confidence = rounded(min(92.0 if model_used else 72.0, 48.0 + len(frame_results) * 2.2 + (12.0 if model_used else 0.0) - min(20.0, score_movement)))
        synthetic_i, deepfake_i, filters_i = rounded(synthetic), rounded(deepfake), rounded(filters)
        risk, verdict, detail = verdict_for(authenticity, synthetic_i, deepfake_i, filters_i)
        signals = [
            {"name": "Peak sampled-frame risk", "score": rounded(max(float(np.max(synthetic_values)), float(np.max(deepfake_values)))), "detail": f"The strongest sampled visual anomaly appeared near {peak_timestamp:.2f} seconds."},
            {"name": "Temporal inconsistency", "score": rounded(temporal_signal), "detail": "Measures how sharply synthetic/deepfake risk changes across sampled frames."},
            {"name": "Synthetic-generation pattern", "score": synthetic_i, "detail": "Aggregates the median and peak synthetic score across representative frames."},
            {"name": "Face manipulation", "score": deepfake_i, "detail": "Aggregates facial and recompression evidence across sampled frames."},
            {"name": "Filter and retouching", "score": filters_i, "detail": "Measures smoothing and enhancement signals across the clip."},
        ]
        signals.sort(key=lambda item: item["score"], reverse=True)
        evidence = None
        if peak_image is not None:
            resized_peak = resize_image(peak_image, MAX_VIDEO_ANALYSIS_DIM)
            evidence, _, _, _ = ela_map(resized_peak)

        return {
            "filename": filename,
            "media_type": "video",
            "authenticity_score": authenticity,
            "synthetic_probability": synthetic_i,
            "deepfake_probability": deepfake_i,
            "filter_probability": filters_i,
            "confidence": confidence,
            "risk": risk,
            "verdict": verdict,
            "verdict_detail": detail,
            "explanation": build_explanation(risk, model_used, synthetic_i, deepfake_i, filters_i, confidence) + f" VeriSight sampled {len(frames)} frames across {duration:.1f} seconds; audio was not analyzed.",
            "signals": signals,
            "strongest_signals": signals[:3],
            "next_steps": [
                "Review the original clip around the peak timestamp frame by frame.",
                "Check the source account, upload history and an uncompressed original when available.",
                "Do not treat visual screening as voice-clone or full-frame proof.",
            ],
            "model": {
                "used": model_used,
                "mode": f"Neural + forensic on sampled frames ({MODEL_ID})" if model_used else "Forensic fallback on sampled frames",
                "status": DETECTOR.status,
            },
            "video": {
                "duration": round(duration, 3),
                "fps": round(fps, 3),
                "frame_count": frame_count,
                "sampled_frames": len(frames),
                "peak_timestamp": round(peak_timestamp, 3),
                "frames": frames,
                "audio_analyzed": False,
            },
            "technical": {
                "sample_interval_target": VIDEO_SAMPLE_SECONDS,
                "sample_limit": MAX_VIDEO_FRAMES,
                "temporal_score_std": round(score_movement, 3),
            },
            "evidence_image": data_url(evidence, "JPEG", 80) if evidence else None,
            "processing_ms": int((time.perf_counter() - started) * 1000),
        }
    finally:
        if capture is not None:
            capture.release()
        if temporary_path:
            try:
                os.remove(temporary_path)
            except OSError:
                pass
