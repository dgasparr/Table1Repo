"""A13 stress test: where does detection + measurement break? Owner: Pair A.

Synthetic photos only (no camera needed). For each camera angle x distance x blur:
  - draw the 2x2 board with hand-drawn wobble on a wall (Sharpie cell corners jittered),
  - photograph it with a pinhole model of a 12 MP phone main lens (~69 deg HFOV),
  - add blur, sensor noise and JPEG compression,
  - run measure.detect() and measure two known on-plane lines:
      12 in  : just below the board (typical "near" measurement)
      48 in  : a door-width reach starting at the board (extrapolation)
  - record found / grade / error / whether |error| <= 2 x the reported +/- (A12 honesty check).

    python stress_test.py            # ~1-2 min; prints tables, writes stress_results.csv
"""
import csv
import time

import cv2
import numpy as np

import markers
import measure

IMG_W, IMG_H = 4032, 3024                      # 12 MP phone
F_PX = IMG_W / 2 / np.tan(np.radians(69 / 2))  # main 1x lens, ~69 deg horizontal FOV
TEX_PX_PER_MM = 5.0                            # resolution of the drawn wall texture
WALL_ORIGIN_MM = (-110.0, -60.0)               # wall texture top-left, in board-plane mm
WALL_SIZE_MM = (400.0, 330.0)
WOBBLE_MM = 0.35                               # hand-drawn cell-corner jitter (1 sigma)
MARKER_SHIFT_MM = 0.3                          # whole-marker placement error (1 sigma)

ANGLES = [0, 15, 30, 45, 60, 70, 75]           # camera yaw from straight-on, degrees
DIST_FT = [3, 6, 10, 15, 20]                   # camera to board centre
BLURS = {"sharp": 0.7, "shaky": 2.0}           # Gaussian sigma, px
SEEDS = [0, 1, 2]

BOARD = markers.DEFAULT_BOARD
C = BOARD.size_mm / 2
LINES = {  # name: (p1_mm, p2_mm, true_in), in board-plane mm (origin = ID 0 top-left)
    "12in": ((C - 152.4, BOARD.size_mm + 40), (C + 152.4, BOARD.size_mm + 40), 12.0),
    "48in": ((0.0, BOARD.size_mm + 80), (1219.2, BOARD.size_mm + 80), 48.0),
}


def draw_wall(rng) -> np.ndarray:
    """Board with hand-drawn wobble, rendered as a flat wall texture."""
    w, h = (int(v * TEX_PX_PER_MM) for v in WALL_SIZE_MM)
    wall = np.full((h, w), 235, np.uint8)  # off-white paper
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, BOARD.dictionary))
    cell = BOARD.marker_mm / markers.MARKER_CELLS
    for mid, quad in BOARD.object_points().items():
        bits = cv2.aruco.generateImageMarker(d, mid, markers.MARKER_CELLS)  # 6x6, 0 = black
        x0, y0 = quad[0] + rng.normal(0, MARKER_SHIFT_MM, 2)
        n = markers.MARKER_CELLS + 1
        gx, gy = np.meshgrid(np.arange(n) * cell, np.arange(n) * cell)
        gx = gx + x0 + rng.normal(0, WOBBLE_MM, gx.shape)
        gy = gy + y0 + rng.normal(0, WOBBLE_MM, gy.shape)
        for r in range(markers.MARKER_CELLS):
            for c in range(markers.MARKER_CELLS):
                if bits[r, c] < 128:
                    pts = np.array([[gx[r, c], gy[r, c]], [gx[r, c + 1], gy[r, c + 1]],
                                    [gx[r + 1, c + 1], gy[r + 1, c + 1]], [gx[r + 1, c], gy[r + 1, c]]])
                    px = ((pts - WALL_ORIGIN_MM) * TEX_PX_PER_MM * 16).astype(np.int32)
                    cv2.fillConvexPoly(wall, px, 20, lineType=cv2.LINE_AA, shift=4)
    return wall


def camera_homography(angle_deg: float, dist_mm: float) -> np.ndarray:
    """3x3 homography: board-plane mm -> image px, camera yawed by angle and aimed at the board centre."""
    target = np.array([C, C, 0.0])
    a = np.radians(angle_deg)
    cam = target + dist_mm * np.array([np.sin(a), 0.0, -np.cos(a)])
    f = (target - cam) / np.linalg.norm(target - cam)
    x = np.cross([0.0, 1.0, 0.0], f); x /= np.linalg.norm(x)
    y = np.cross(f, x)
    R = np.vstack([x, y, f])
    t = -R @ cam
    K = np.array([[F_PX, 0, IMG_W / 2], [0, F_PX, IMG_H / 2], [0, 0, 1]])
    return K @ np.column_stack([R[:, 0], R[:, 1], t])


def photograph(wall, H_plane, blur, rng) -> np.ndarray:
    tex_to_mm = np.array([[1 / TEX_PX_PER_MM, 0, WALL_ORIGIN_MM[0]],
                          [0, 1 / TEX_PX_PER_MM, WALL_ORIGIN_MM[1]], [0, 0, 1]])
    img = cv2.warpPerspective(wall, H_plane @ tex_to_mm, (IMG_W, IMG_H),
                              flags=cv2.INTER_AREA, borderValue=150)
    img = cv2.GaussianBlur(img, (0, 0), blur)
    img = np.clip(img + rng.normal(0, 3, img.shape), 0, 255).astype(np.uint8)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return cv2.cvtColor(cv2.imdecode(jpg, cv2.IMREAD_GRAYSCALE), cv2.COLOR_GRAY2BGR)


def run_case(angle, dist_ft, blur_name, seed):
    rng = np.random.default_rng(1000 * seed + 10 * angle + dist_ft)
    H_plane = camera_homography(angle, dist_ft * 304.8)
    img = photograph(draw_wall(rng), H_plane, BLURS[blur_name], rng)
    det = measure.detect(img)
    row = {"angle": angle, "dist_ft": dist_ft, "blur": blur_name, "seed": seed,
           "found": det.found, "n_markers": len(det.ids), "grade": det.grade, "rms_mm": det.rms_mm}
    for name, (a, b, true_in) in LINES.items():
        if not det.found:
            row.update({f"{name}_err_in": None, f"{name}_unc_in": None, f"{name}_covered": None})
            continue
        p = markers.apply_homography(H_plane, [a, b])
        mm, unc, _ = measure.distance_with_uncertainty(det, tuple(p[0]), tuple(p[1]))
        err = mm / 25.4 - true_in
        row.update({f"{name}_err_in": round(err, 4), f"{name}_unc_in": round(unc / 25.4, 4),
                    f"{name}_covered": abs(err) <= 2 * unc / 25.4})
    return row


def fmt_cell(rows, key):
    found = [r for r in rows if r["found"]]
    if not found:
        return "   not found"
    errs = [abs(r[key]) for r in found]
    grades = "".join({"green": "G", "yellow": "Y", "red": "R"}[r["grade"]] for r in found)
    miss = len(rows) - len(found)
    return f'{max(errs):5.3f}" {grades:<3}' + (f" {miss}x" if miss else "   ")


def main():
    t0 = time.perf_counter()
    rows = [run_case(a, d, b, s) for b in BLURS for a in ANGLES for d in DIST_FT for s in SEEDS]
    with open("stress_results.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)

    print(f"{len(rows)} synthetic photos in {time.perf_counter() - t0:.0f} s. "
          f"Cell = worst |error| over {len(SEEDS)} boards, then grades (G/Y/R), then 'Nx' = N not found.\n")
    for line in LINES:
        for b in BLURS:
            print(f"== {line} line, {b} photo ==")
            print("angle | " + " | ".join(f"{d:>2} ft          " for d in DIST_FT))
            for a in ANGLES:
                cells = [fmt_cell([r for r in rows if r["angle"] == a and r["dist_ft"] == d and r["blur"] == b],
                                  f"{line}_err_in") for d in DIST_FT]
                print(f"{a:>4}° | " + " | ".join(f"{c:<16}" for c in cells))
            print()

    found = [r for r in rows if r["found"]]
    print(f"Detection: {len(found)}/{len(rows)} photos found the board.")
    for line in LINES:
        cov = [r[f"{line}_covered"] for r in found]
        print(f"A12 honesty, {line}: true error within 2x the shown ± in {sum(cov)}/{len(cov)} "
              f"({100 * sum(cov) / len(cov):.0f}%) of found photos.")
    by_grade = {}
    for r in found:
        by_grade.setdefault(r["grade"], []).append(abs(r["12in_err_in"]))
    for g in ["green", "yellow", "red"]:
        if g in by_grade:
            e = np.array(by_grade[g])
            print(f"Grade {g:>6}: {len(e):3d} photos, 12in error median {np.median(e):.3f}\" / max {e.max():.3f}\"")


if __name__ == "__main__":
    main()
