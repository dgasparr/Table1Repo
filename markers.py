"""
markers.py - detection, calibration and measurement for the hand-drawn
2x2 ArUco calc pad target.

Target (see calcpad_marker_template.pdf):
    OpenCV DICT_4X4_50, IDs 0-3, laid out as you look at the sheet:
        ID 0 | ID 1
        -----+-----
        ID 2 | ID 3
    Sheet B uses IDs 4-7 in the same layout (Board(first_id=4)).
    Default board: 1/8 in grid squares, 4 squares per marker cell (1/2 in),
    8 squares gap (1 in) -> 3 in markers, 7 in x 7 in board.

Coordinate conventions
    image points : pixels in the image as loaded (EXIF rotation already applied)
    plane points : mm on the paper plane; origin = top-left corner of ID 0,
                   x to the right, y down the sheet

Scope (v0.1): measurements are valid ONLY for points on the paper's plane.
Off-plane measurement (vanishing points, pose, LiDAR, etc.) comes later.

Library use (backend):
    import markers
    img = markers.decode_image(upload_bytes)
    cal = markers.calibrate(img)                     # JSON-serialisable dict
    if cal["status"] == "ready":
        m = markers.measure(cal, (x1, y1), (x2, y2))  # dict with mm, in, uncertainty
        rect, _ = markers.rectify(img, cal)
        overlay = markers.draw_overlay(img, cal)

CLI:
    python markers.py photo.jpg
    python markers.py photo.jpg --measure 100,200,400,220 --out results/

Requires: opencv-contrib-python (or opencv-python >= 4.7), numpy
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass

import cv2
import numpy as np

SOLVER_VERSION = "0.1.0"
MM_PER_IN = 25.4
MARKER_CELLS = 6  # 4x4 data bits + 1-cell black border on each side
LAYOUT = {0: (0, 0), 1: (1, 0), 2: (0, 1), 3: (1, 1)}  # id - first_id -> (col, row)


# ---------------------------------------------------------------------------
# Board definition
# ---------------------------------------------------------------------------
@dataclass
class Board:
    square_in: float = 0.125   # size of one grid square on the pad, inches
    cell: float = 4            # grid squares per marker cell
    gap: float = 8             # grid squares between markers
    dictionary: str = "DICT_4X4_50"
    first_id: int = 0          # 0 = sheet A (IDs 0-3), 4 = sheet B (IDs 4-7)

    @property
    def square_mm(self) -> float:
        return self.square_in * MM_PER_IN

    @property
    def marker_mm(self) -> float:
        return MARKER_CELLS * self.cell * self.square_mm

    @property
    def gap_mm(self) -> float:
        return self.gap * self.square_mm

    @property
    def size_mm(self) -> float:
        return 2 * self.marker_mm + self.gap_mm

    def object_points(self) -> dict[int, np.ndarray]:
        """Plane coords (mm) of each marker's corners, OpenCV order TL, TR, BR, BL."""
        pitch = self.marker_mm + self.gap_mm
        s = self.marker_mm
        out = {}
        for k, (col, row) in LAYOUT.items():
            x0, y0 = col * pitch, row * pitch
            out[self.first_id + k] = np.array([[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]],
                                dtype=np.float64)
        return out


DEFAULT_BOARD = Board()


# ---------------------------------------------------------------------------
# Image I/O
# ---------------------------------------------------------------------------
def decode_image(data: bytes) -> np.ndarray:
    """Decode uploaded JPEG/PNG bytes to a BGR image.
    OpenCV applies the EXIF orientation flag when decoding.
    HEIC is NOT supported by OpenCV - convert first (e.g. pillow-heif) on the backend."""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image (unsupported format or corrupt file)")
    return img


def load_image(path: str) -> np.ndarray:
    with open(path, "rb") as f:
        return decode_image(f.read())


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------
def _detector(dictionary: str) -> cv2.aruco.ArucoDetector:
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary))
    p = cv2.aruco.DetectorParameters()
    # Tuned for hand-drawn markers on gridded paper
    p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    p.adaptiveThreshWinSizeMax = 53
    p.polygonalApproxAccuracyRate = 0.05
    p.errorCorrectionRate = 0.8
    return cv2.aruco.ArucoDetector(d, p)


def detect_all(img: np.ndarray, dictionary: str = DEFAULT_BOARD.dictionary) -> dict[int, np.ndarray]:
    """Return {marker_id: 4x2 corner array (px)} for every ID in the dictionary found."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    corners, ids, _ = _detector(dictionary).detectMarkers(gray)
    found = {}
    if ids is not None:
        for c, i in zip(corners, ids.flatten()):
            i = int(i)
            if i not in found:  # ignore duplicates
                found[i] = c.reshape(4, 2).astype(np.float64)
    return found


def detect_markers(img: np.ndarray, board: Board = DEFAULT_BOARD, all_found: dict | None = None
                   ) -> dict[int, np.ndarray]:
    """Return {marker_id: 4x2 corner array (px)} for this board's IDs found in the image.
    Pass all_found (from detect_all) to reuse one detection pass across several boards."""
    if all_found is None:
        all_found = detect_all(img, board.dictionary)
    return {i: c for i, c in all_found.items() if i - board.first_id in LAYOUT}


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
def _grade(n_markers: int, rms_mm: float) -> str:
    if n_markers == 4 and rms_mm < 1.0:
        return "A"
    if n_markers >= 2 and rms_mm < 2.0:
        return "B"
    if n_markers >= 1:
        return "C"
    return "none"


def calibrate(img: np.ndarray, board: Board = DEFAULT_BOARD, all_found: dict | None = None) -> dict:
    """Detect the target and solve the image -> paper-plane homography.

    Returns a JSON-serialisable calibration record. status is:
        "ready"            usable calibration
        "needs_reference"  no target found; user must add a manual reference
    """
    h, w = img.shape[:2]
    record = {
        "method": "aruco_gridboard_2x2",
        "solver_version": SOLVER_VERSION,
        "image_size": [w, h],
        "board": asdict(board),
        "plane_units": "mm",
        "markers_found": [],
        "status": "needs_reference",
        "grade": "none",
        "warnings": [],
    }

    found = detect_markers(img, board, all_found)
    if not found:
        record["warnings"].append("No target markers found.")
        return record

    obj = board.object_points()
    ids = sorted(found)
    img_pts = np.vstack([found[i] for i in ids])
    plane_pts = np.vstack([obj[i] for i in ids])

    H, _ = cv2.findHomography(img_pts, plane_pts, method=0)
    if H is None:
        record["warnings"].append("Homography solve failed.")
        return record
    H = H / H[2, 2]

    proj = apply_homography(H, img_pts)
    err = np.linalg.norm(proj - plane_pts, axis=1)
    rms = float(np.sqrt(np.mean(err ** 2)))

    # Approximate image scale at the board, used for uncertainty estimates
    px_per_mm = _local_px_per_mm(np.linalg.inv(H), plane_pts.mean(axis=0))
    # Corner noise: from residual when we have redundancy, else a conservative default
    if len(ids) >= 2:
        sigma_px = max(0.3, rms * px_per_mm)
    else:
        sigma_px = 1.0

    if len(ids) == 1:
        record["warnings"].append("Only one marker found: no redundancy, accuracy unchecked.")
    if rms > 2.0:
        record["warnings"].append(
            "Large corner residual: a marker may be drawn off-grid, the sheet may not be flat, "
            "or the board settings don't match the drawing.")
    if px_per_mm < 1.0:
        record["warnings"].append("Target is small in the image; move closer or use a larger target.")

    record.update({
        "status": "ready",
        "markers_found": ids,
        "homography": H.tolist(),                 # image px -> plane mm
        "homography_inv": np.linalg.inv(H).tolist(),  # plane mm -> image px
        "image_points": img_pts.tolist(),
        "plane_points": plane_pts.tolist(),
        "residual_mm": {"rms": round(rms, 3), "max": round(float(err.max()), 3)},
        "px_per_mm_at_target": round(px_per_mm, 3),
        "corner_sigma_px": round(sigma_px, 3),
        "grade": _grade(len(ids), rms),
    })
    return record


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def apply_homography(H, pts) -> np.ndarray:
    """Map Nx2 points through a 3x3 homography."""
    H = np.asarray(H, dtype=np.float64)
    pts = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
    return cv2.perspectiveTransform(pts, H).reshape(-1, 2)


def _local_px_per_mm(H_inv: np.ndarray, plane_pt) -> float:
    p = np.array([plane_pt, plane_pt + [1.0, 0.0], plane_pt + [0.0, 1.0]])
    q = apply_homography(H_inv, p)
    return float((np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[0])) / 2)


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------
def measure(cal: dict, p1, p2, n_samples: int = 300, seed: int = 0) -> dict:
    """Distance between two image points (px), both assumed on the paper plane.

    Uncertainty: Monte Carlo - perturb detected corners by corner_sigma_px,
    re-solve the homography, take the spread (1 sigma). Click placement error
    is NOT included; add it in the UI if desired.
    """
    if cal.get("status") != "ready":
        raise ValueError("Calibration not ready; cannot measure.")
    H = np.asarray(cal["homography"])
    img_pts = np.asarray(cal["image_points"])
    plane_pts = np.asarray(cal["plane_points"])
    sigma = float(cal["corner_sigma_px"])
    pts = np.array([p1, p2], dtype=np.float64)

    q = apply_homography(H, pts)
    d = float(np.linalg.norm(q[1] - q[0]))

    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(n_samples):
        noisy = img_pts + rng.normal(0, sigma, img_pts.shape)
        Hs, _ = cv2.findHomography(noisy, plane_pts, method=0)
        if Hs is None:
            continue
        qs = apply_homography(Hs, pts)
        samples.append(np.linalg.norm(qs[1] - qs[0]))
    unc = float(np.std(samples)) if samples else float("nan")

    # Extrapolation: how far the measured points lie from the target, in board sizes
    board_size = Board(**cal["board"]).size_mm
    centre = plane_pts.mean(axis=0)
    extrap = float(np.max(np.linalg.norm(q - centre, axis=1)) / board_size)

    warnings = []
    if extrap > 3:
        warnings.append(f"Points are {extrap:.1f}x the target size away from it; "
                        "accuracy degrades with distance.")
    warnings.append("Valid only if both points lie on the same plane as the target sheet.")

    return {
        "distance_mm": round(d, 2),
        "distance_in": round(d / MM_PER_IN, 3),
        "uncertainty_mm": round(unc, 2),
        "uncertainty_in": round(unc / MM_PER_IN, 3),
        "plane_points_mm": q.round(2).tolist(),
        "extrapolation_factor": round(extrap, 2),
        "grade": cal["grade"],
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Visual outputs
# ---------------------------------------------------------------------------
def rectify(img: np.ndarray, cal: dict, px_per_mm: float = 4.0, margin_mm: float = 150.0,
            max_side_px: int = 6000) -> tuple[np.ndarray, list]:
    """Top-down view of the paper plane around the target.

    Returns (image, M) where M (3x3, list) maps ORIGINAL image px -> rectified px.
    Rectified px -> plane mm:  x_mm = x_px / px_per_mm - margin_mm  (same for y).
    """
    H = np.asarray(cal["homography"])
    size_mm = Board(**cal["board"]).size_mm + 2 * margin_mm
    side = int(size_mm * px_per_mm)
    if side > max_side_px:
        px_per_mm = max_side_px / size_mm
        side = max_side_px
    S = np.array([[px_per_mm, 0, margin_mm * px_per_mm],
                  [0, px_per_mm, margin_mm * px_per_mm],
                  [0, 0, 1]])
    M = S @ H
    out = cv2.warpPerspective(img, M, (side, side), flags=cv2.INTER_LINEAR)
    return out, M.tolist()


def draw_overlay(img: np.ndarray, cal: dict, color=(0, 200, 0)) -> np.ndarray:
    """Original image with detected marker outlines (in `color`, BGR), IDs and the board outline."""
    vis = img.copy()
    t = max(2, int(round(max(img.shape[:2]) / 600)))
    if cal.get("status") != "ready":
        return vis
    pts = np.asarray(cal["image_points"]).reshape(-1, 4, 2)
    for mid, quad in zip(cal["markers_found"], pts):
        q = quad.astype(np.int32)
        cv2.polylines(vis, [q], True, color, t)
        cv2.circle(vis, tuple(q[0]), t * 3, (0, 0, 255), -1)  # top-left corner
        cv2.putText(vis, f"ID {mid}", tuple(q[0] + [t * 4, -t * 4]),
                    cv2.FONT_HERSHEY_SIMPLEX, t * 0.5, (0, 0, 255), t)
    s = Board(**cal["board"]).size_mm
    outline = apply_homography(cal["homography_inv"], [[0, 0], [s, 0], [s, s], [0, s]])
    cv2.polylines(vis, [outline.astype(np.int32)], True, (255, 140, 0), t)
    return vis


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Calibrate a photo from the calc pad target and measure.")
    ap.add_argument("image")
    ap.add_argument("--square-in", type=float, default=DEFAULT_BOARD.square_in)
    ap.add_argument("--cell", type=float, default=DEFAULT_BOARD.cell)
    ap.add_argument("--gap", type=float, default=DEFAULT_BOARD.gap)
    ap.add_argument("--measure", help="x1,y1,x2,y2 in original image pixels")
    ap.add_argument("--out", default=".", help="folder for calibration.json, overlay.jpg, rectified.jpg")
    a = ap.parse_args()

    board = Board(square_in=a.square_in, cell=a.cell, gap=a.gap)
    img = load_image(a.image)
    cal = calibrate(img, board)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "calibration.json"), "w") as f:
        json.dump(cal, f, indent=2)

    print(f"Status: {cal['status']}   grade: {cal['grade']}   markers: {cal['markers_found']}")
    for w in cal["warnings"]:
        print(f"  ! {w}")
    if cal["status"] != "ready":
        sys.exit(1)
    print(f"Corner residual: rms {cal['residual_mm']['rms']} mm, max {cal['residual_mm']['max']} mm")

    cv2.imwrite(os.path.join(a.out, "overlay.jpg"), draw_overlay(img, cal))
    rect, _ = rectify(img, cal)
    cv2.imwrite(os.path.join(a.out, "rectified.jpg"), rect)
    print(f"Wrote calibration.json, overlay.jpg, rectified.jpg to {a.out}")

    if a.measure:
        x1, y1, x2, y2 = map(float, a.measure.split(","))
        m = measure(cal, (x1, y1), (x2, y2))
        print(f"Distance: {m['distance_in']} in  +/- {m['uncertainty_in']} in   "
              f"({m['distance_mm']} mm +/- {m['uncertainty_mm']} mm)")
        for w in m["warnings"]:
            print(f"  ! {w}")


if __name__ == "__main__":
    main()
