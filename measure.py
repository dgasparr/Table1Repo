"""Detection + measurement contract. Owner: Pair A.

Thin wrapper over markers.py (Benjamin's calc pad solver) that exposes the frozen
interface in ARCHITECTURE.md. app.py should only import from here.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

import markers

GRADES = ["green", "yellow", "red"]
GRADE_BGR = {"green": (0, 200, 0), "yellow": (0, 200, 255), "red": (0, 0, 255), "none": (128, 128, 128)}
SHEETS = [markers.Board(first_id=0), markers.Board(first_id=4)]  # sheet A: IDs 0-3, sheet B: IDs 4-7


@dataclass
class Detection:
    found: bool
    ids: list[int] = field(default_factory=list)
    corners_px: list[np.ndarray] = field(default_factory=list)
    H: np.ndarray | None = None
    rms_mm: float | None = None
    grade: str = "none"
    message: str = ""
    cal: dict | None = None  # full markers.calibrate() record (uncertainty, rectify, etc.)


def _grade(rms_mm: float, n_markers: int) -> tuple[str, list[str]]:
    level = 0 if rms_mm < 1.0 else 1 if rms_mm <= 2.0 else 2
    notes = []
    if n_markers < 4:
        # Fewer corners = less redundancy, so the residual is less trustworthy
        level = min(level + 1, 2)
        notes.append(f"Only {n_markers} of 4 markers found; grade lowered one level.")
    return GRADES[level], notes


def detect(image_bgr: np.ndarray) -> Detection:
    # One detection pass, then use whichever sheet (A or B) shows the most markers
    all_found = markers.detect_all(image_bgr)
    counts = [len(markers.detect_markers(image_bgr, b, all_found)) for b in SHEETS]
    best = SHEETS[int(np.argmax(counts))]
    cal = markers.calibrate(image_bgr, best, all_found)
    if cal["status"] != "ready":
        msg = " ".join(cal["warnings"]) or "Target not found."
        return Detection(False, grade="none", message=msg + " Check the capture rules and retake.", cal=cal)

    ids = cal["markers_found"]
    corners = list(np.asarray(cal["image_points"]).reshape(-1, 4, 2))
    rms = cal["residual_mm"]["rms"]
    grade, notes = _grade(rms, len(ids))
    if min(counts) > 0:
        notes.append("Both sheets visible; using the one with more markers.")
    sheet = "A" if best.first_id == 0 else "B"
    msg = " ".join(notes + cal["warnings"]) or f"Sheet {sheet}: all 4 markers found, corner fit {rms:.2f} mm."
    return Detection(True, ids, corners, np.asarray(cal["homography"]), rms, grade, msg, cal)


def distance_mm(H, p1, p2) -> float:
    pts = cv2.perspectiveTransform(np.array([[p1, p2]], dtype=np.float64), H)[0]
    return float(np.linalg.norm(pts[1] - pts[0]))


def area_mm2(H, points) -> float:
    pts = cv2.perspectiveTransform(np.array([points], dtype=np.float64), H)[0]
    return float(abs(cv2.contourArea(pts.astype(np.float32))))


def fmt_ft_in(mm: float, denom: int = 16) -> str:
    """1234.0 -> 4'-0 9/16". Rounded to the nearest 1/denom inch."""
    sign = "-" if mm < 0 else ""
    n = round(abs(mm) / 25.4 * denom)  # total length in 1/denom-inch units
    ft, rem = divmod(n, 12 * denom)
    inch, frac = divmod(rem, denom)
    if frac:
        g = np.gcd(frac, denom)
        return f"{sign}{ft}'-{inch} {frac // g}/{denom // g}\""
    return f"{sign}{ft}'-{inch}\""


def draw_overlay(image_bgr: np.ndarray, det: Detection) -> np.ndarray:
    if det.cal is not None:
        return markers.draw_overlay(image_bgr, det.cal, GRADE_BGR[det.grade])
    return image_bgr.copy()
