"""Runtime-safe exports and compatibility patches for the forensic analyzer."""

from __future__ import annotations

import numpy as np

from . import analyzer as _analyzer


def _safe_blockiness_score(gray: np.ndarray) -> float:
    """Compare exact JPEG-grid boundaries without shape-mismatch edge cases."""
    height, width = gray.shape[:2]
    if height < 18 or width < 18:
        return 0.0

    vertical_boundaries = np.arange(8, width, 8, dtype=np.int32)
    horizontal_boundaries = np.arange(8, height, 8, dtype=np.int32)
    vertical_regular = np.arange(5, width, 8, dtype=np.int32)
    horizontal_regular = np.arange(5, height, 8, dtype=np.int32)

    vertical_boundary_value = (
        np.abs(gray[:, vertical_boundaries].astype(np.float32) - gray[:, vertical_boundaries - 1].astype(np.float32)).mean()
        if vertical_boundaries.size else 0.0
    )
    horizontal_boundary_value = (
        np.abs(gray[horizontal_boundaries, :].astype(np.float32) - gray[horizontal_boundaries - 1, :].astype(np.float32)).mean()
        if horizontal_boundaries.size else 0.0
    )
    vertical_regular_value = (
        np.abs(gray[:, vertical_regular].astype(np.float32) - gray[:, vertical_regular - 1].astype(np.float32)).mean()
        if vertical_regular.size else 0.0
    )
    horizontal_regular_value = (
        np.abs(gray[horizontal_regular, :].astype(np.float32) - gray[horizontal_regular - 1, :].astype(np.float32)).mean()
        if horizontal_regular.size else 0.0
    )

    return max(
        0.0,
        float(
            (vertical_boundary_value + horizontal_boundary_value)
            - (vertical_regular_value + horizontal_regular_value)
        ),
    )


_analyzer.blockiness_score = _safe_blockiness_score

DETECTOR = _analyzer.DETECTOR
analyze_image_bytes = _analyzer.analyze_image_bytes
analyze_video_bytes = _analyzer.analyze_video_bytes
