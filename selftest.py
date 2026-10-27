"""Synthetic self-test for markers.py / measure.py. Owner: Pair A.

Renders the 2x2 board at exact size on a "wall", warps it to an oblique view,
adds blur + noise, then checks detection and a known on-plane distance.

    python selftest.py            # prints results, writes selftest_photo.jpg
"""
import cv2
import numpy as np

import markers

PX_PER_MM = 4.0          # resolution of the flat "wall" before warping
WALL_MM = (600, 450)     # wall area rendered, mm (w, h)
BOARD_AT_MM = (150, 100) # top-left of ID 0 on the wall, mm
KNOWN_MM = 8 * 25.4      # test segment length, 8 in


def render_wall(board=markers.DEFAULT_BOARD):
    w, h = (int(v * PX_PER_MM) for v in WALL_MM)
    wall = np.full((h, w), 255, np.uint8)
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, board.dictionary))
    side = int(round(board.marker_mm * PX_PER_MM))
    for mid, quad in board.object_points().items():
        x0 = int(round((BOARD_AT_MM[0] + quad[0, 0]) * PX_PER_MM))
        y0 = int(round((BOARD_AT_MM[1] + quad[0, 1]) * PX_PER_MM))
        wall[y0:y0 + side, x0:x0 + side] = cv2.aruco.generateImageMarker(d, mid, side)
    # Known segment on the same plane, below the board: from (150, 330) mm, 8 in long
    a = np.array([150.0, 330.0])
    b = a + [KNOWN_MM, 0.0]
    cv2.line(wall, tuple((a * PX_PER_MM).astype(int)), tuple((b * PX_PER_MM).astype(int)), 0, 3)
    return cv2.cvtColor(wall, cv2.COLOR_GRAY2BGR), a, b


def oblique_photo(wall):
    h, w = wall.shape[:2]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    # Roughly a 30-40 deg yaw plus some tilt, into a 3000x2250 "phone" frame
    dst = np.float32([[400, 300], [2500, 520], [2450, 1900], [380, 2050]])
    M = cv2.getPerspectiveTransform(src, dst)
    photo = cv2.warpPerspective(wall, M, (3000, 2250), borderValue=(200, 200, 200))
    photo = cv2.GaussianBlur(photo, (5, 5), 1.2)
    noise = np.random.default_rng(1).normal(0, 4, photo.shape)
    photo = np.clip(photo + noise, 0, 255).astype(np.uint8)
    return photo, M


def main():
    wall, a_mm, b_mm = render_wall()
    photo, M = oblique_photo(wall)
    cv2.imwrite("selftest_photo.jpg", photo)

    cal = markers.calibrate(photo)
    print(f"status={cal['status']} grade={cal['grade']} ids={cal['markers_found']} "
          f"residual={cal.get('residual_mm')}")
    assert cal["status"] == "ready" and cal["markers_found"] == [0, 1, 2, 3]

    # Segment endpoints in photo px
    p = cv2.perspectiveTransform(np.array([[a_mm, b_mm]]) * PX_PER_MM, M)[0]
    m = markers.measure(cal, p[0], p[1])
    err = m["distance_in"] - KNOWN_MM / 25.4
    print(f"known 8.000 in -> measured {m['distance_in']:.3f} in "
          f"(+/- {m['uncertainty_in']:.3f}), error {err:+.3f} in")
    assert abs(err) < 0.05

    import measure
    det = measure.detect(photo)
    d = measure.distance_mm(det.H, tuple(p[0]), tuple(p[1]))
    print(f"measure.detect: found={det.found} ids={det.ids} rms={det.rms_mm} grade={det.grade} "
          f"| distance_mm={d:.2f} | {det.message}")
    assert det.found and det.ids == [0, 1, 2, 3] and det.rms_mm < 1 and det.grade == "green"
    assert abs(d - KNOWN_MM) < 1.3

    blank = measure.detect(np.full((800, 800, 3), 255, np.uint8))
    print(f"blank image: found={blank.found} grade={blank.grade} | {blank.message}")
    assert not blank.found and blank.grade == "none"

    # Cover ID 3 (bottom-right marker) -> partial board, grade lowered
    covered = photo.copy()
    q3 = np.asarray(cal["image_points"]).reshape(-1, 4, 2)[3].astype(np.int32)
    cv2.fillConvexPoly(covered, cv2.convexHull(q3), (255, 255, 255))
    part = measure.detect(covered)
    print(f"ID 3 covered: found={part.found} ids={part.ids} grade={part.grade} | {part.message}")
    assert part.found and part.ids == [0, 1, 2] and part.grade == "yellow"
    # Sheet B (IDs 4-7)
    photo_b, M_b = oblique_photo(render_wall(markers.Board(first_id=4))[0])
    det_b = measure.detect(photo_b)
    print(f"sheet B: found={det_b.found} ids={det_b.ids} grade={det_b.grade} | {det_b.message}")
    assert det_b.ids == [4, 5, 6, 7] and det_b.grade == "green"

    # Timing on a 12 MP frame (Pair B question)
    import time
    big = cv2.resize(photo, (4032, 3024))
    t0 = time.perf_counter(); det_big = measure.detect(big); t1 = time.perf_counter()
    measure.draw_overlay(big, det_big); t2 = time.perf_counter()
    print(f"12 MP timing: detect {t1 - t0:.2f} s, draw_overlay {t2 - t1:.3f} s")

    # A12: uncertainty
    t0 = time.perf_counter()
    mm_u, unc, warn = measure.distance_with_uncertainty(det, tuple(p[0]), tuple(p[1]))
    t_unc = time.perf_counter() - t0
    print(f"A12: {measure.fmt_ft_in(mm_u)} {measure.fmt_pm(unc)} (unc {unc:.2f} mm, {t_unc * 1000:.0f} ms) "
          f"warn='{warn}'")
    assert abs(mm_u - d) < 1e-6 and 0 <= unc < 1.6
    far = measure.distance_with_uncertainty(det, tuple(p[0]), (photo.shape[1] - 1.0, photo.shape[0] - 1.0))
    print(f"A12 far point: {measure.fmt_pm(far[1])} warn='{far[2]}'")
    pm = measure.fmt_pm
    assert pm(0.5) == '± <1/16"' and pm(1.6) == '± 1/16"' and pm(3.2) == '± 1/8"'
    assert pm(25.4 * 1.25) == '± 1 1/4"' and pm(25.4) == '± 1"' and pm(float("nan")) == "± ?"

    f = measure.fmt_ft_in
    assert f(1234.0) == "4'-0 9/16\"", f(1234.0)
    assert f(7.25 * 25.4) == "0'-7 1/4\""
    assert f((11 + 31 / 32) * 25.4) == "1'-0\""          # rounds up across the foot
    assert f(12 * 25.4) == "1'-0\"" and f(0) == "0'-0\""
    assert f(8.5 * 25.4) == "0'-8 1/2\""
    print("fmt_ft_in OK:", f(1234.0), f(KNOWN_MM))
    print("SELFTEST PASSED")


if __name__ == "__main__":
    main()
