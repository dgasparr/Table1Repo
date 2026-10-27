"""Detection + measurement contract. Owner: Pair A.

STUB: returns fake but correctly typed data so Pair B can build the UI now.
Pair A replaces the bodies; signatures are frozen (see ARCHITECTURE.md).
"""
from dataclasses import dataclass, field

import cv2
import numpy as np


@dataclass
class Detection:
    found: bool
    ids: list[int] = field(default_factory=list)
    corners_px: list[np.ndarray] = field(default_factory=list)
    H: np.ndarray | None = None
    rms_mm: float | None = None
    grade: str = "none"
    message: str = ""


def detect(image_bgr: np.ndarray) -> Detection:
    # STUB: pretend a 76.2 mm (3") marker sits in the top-left corner, 0.5 mm per px.
    s = 76.2 / 0.5
    corners = np.array([[50, 50], [50 + s, 50], [50 + s, 50 + s], [50, 50 + s]], dtype=np.float32)
    H = np.diag([0.5, 0.5, 1.0])
    return Detection(True, [0], [corners], H, 0.4, "green", "STUB detection (fake scale)")


def distance_mm(H, p1, p2) -> float:
    pts = cv2.perspectiveTransform(np.array([[p1, p2]], dtype=np.float64), H)[0]
    return float(np.linalg.norm(pts[1] - pts[0]))


def area_mm2(H, points) -> float:
    pts = cv2.perspectiveTransform(np.array([points], dtype=np.float64), H)[0]
    return float(abs(cv2.contourArea(pts.astype(np.float32))))


def fmt_ft_in(mm: float, denom: int = 16) -> str:
    # STUB: decimal inches. Pair A: return ft-in with fractions, e.g. 4'-0 9/16"
    return f'{mm / 25.4:.2f}"'


def draw_overlay(image_bgr: np.ndarray, det: Detection) -> np.ndarray:
    out = image_bgr.copy()
    for c in det.corners_px:
        cv2.polylines(out, [c.astype(np.int32)], True, (0, 255, 0), 3)
    return out
