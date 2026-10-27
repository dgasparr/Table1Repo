# Pair A — Detection & math

**Team:** Daniel + Benjamin

**Mission:** turn a photo into a trustworthy scale. Implement the real `measure.py` behind the frozen contract in [../ARCHITECTURE.md](../ARCHITECTURE.md).
**You own:** `measure.py`, `markers.py`, `selftest.py`. **Don't edit:** `app.py`, `tests/`, `assets/`.
**Your input:** photos from Pair C in `tests/photos/`. **Your customer:** Pair B calls your functions.

## Block 1 → CP1 (1:45)
- [x] **A1. Push Benjamin's script.** Added as `markers.py`, unchanged.
  *Done when:* it runs from the repo on a synthetic test image. ✅ `selftest.py`: 30–40° oblique view with blur and noise; 4/4 markers, corner fit 0.02 mm, known 8.000" measured as 8.006".
- [x] **A2. Real `detect()`.** Replace the stub body: detect IDs 0–3 (`DICT_4X4_50`, tolerant settings, sub-pixel corners), compute H with all detected corners, compute `rms_mm`, and set the grade (green < 1 mm, yellow 1–2, red > 2, none when not found). Board geometry: cell ½", marker 3", gap 1", ID 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right.
  *Done when:* `detect()` on the synthetic image returns `found=True`, 4 IDs, rms < 1 mm. ✅ It wraps `markers.calibrate()`; a blank image returns found=False with a retake message.
- [x] **A3. `fmt_ft_in()`.** Output `4'-0 9/16"` style, rounded to 1/16". Handle under 1 ft (`0'-7 1/4"`) and inch rollover (11 31/32" → `1'-0"`).
  *Done when:* a few `assert` checks pass. ✅ The asserts are in `selftest.py`.
- [x] **A4. First real photo.** ✅ **GO.** `image01` (wall): 4/4 markers, corner fit 1.04 mm (yellow). `image02` (table, small in frame): 4/4 after a detector tweak (bits sampled from cell centres; it was 2/4 before), 0.86 mm (green). Measured marker edges are 2.96–3.11" against a true 3", which is hand-drawing wobble. Run `detect()` on Pair C's first phone photo of the drawn board.
  *Done when:* you can report found / not found at **CP1 (the go/no-go)**. If not found, try the detector parameters (adaptive threshold window, `minMarkerPerimeterRate`, `polygonalApproxAccuracyRate`) before giving up.

## Block 2 → CP2 (2:45)
- [ ] **A5. Robustness pass.** Run `detect()` on every photo in `tests/photos/`. Print a table of file, found, ids, rms_mm, grade.
  *Done when:* at least 8 of 10 good-practice photos are found; failures are explained (too small, blur, angle, etc.).
- [x] **A6. Partial boards.** ✅ Done along with A2 (covering ID 3 gives yellow). If only 1–3 markers are found, still compute H from what was found, but lower the grade one level and say so in `message`.
- [x] **A7. `draw_overlay()`.** Marker outlines in the grade color, with the ID labels drawn. ✅
- [x] **A7b. Sheet B (IDs 4–7).** `detect()` accepts either sheet and uses the one with the most markers. ✅ Covered in the self-test. Both PDF templates were checked cell by cell against OpenCV IDs 0–7, and all match.
- [ ] ✨ **A8. Accuracy check** (Pair C's error table covers this; only if quick). On 2–3 photos, measure a known on-plane distance (the board's own outer edges, or a letter sheet) and compare it to the truth.
  *Done when:* the error is noted in your Status section.

## Block 3 → CP3 FREEZE (3:45)
- [ ] ✨ **A9. `area_mm2()` verified** on a letter sheet (8.5×11 in = 60,322 mm²).
- [ ] ✨ **A10. Rectified view helper** (`rectify(image, det) -> image`, top-down at about 4 px/mm). Only if Pair B wants it; agree on the signature at CP2.
- [ ] ✨ **A12. "±" uncertainty on every length** (on hold; about 15 min for A + 5 min for B). Shows `8'-4 1/2" ± 1/16"` so engineers know how far to trust a number. Benjamin's `markers.measure()` already computes it: it reruns the solve a few hundred times with tiny corner wobbles and takes the spread, and it warns when the points are far from the board. It adds two functions to the agreed interface, so **agree with Pair B first**:
  ```python
  def distance_with_uncertainty(det, p1, p2) -> tuple[float, float, str]:  # (mm, ±mm 1-sigma, warning or "")
  def fmt_pm(unc_mm) -> str:  # '± 1/16"', or '± <1/16"' when it rounds to zero
  ```
  Pair B: show `f"{fmt_ft_in(mm)} {fmt_pm(unc)}"` plus `warn` as a caption. About 50 ms per call, so cache by `(p1, p2)`. Area mode stays without ±.
- [ ] ✨ **A13. Stress test on synthetic photos** (on hold; about 15 min). Sweep camera angle (0–70°) and board size in the frame; record detection yes/no and error. Output: a small table like "≤45°: under 1/16" · 60°: 1/8" · >70°: not found". It gives tested numbers for the capture-rules cartoon (to Pair C) and a pitch slide. Caveat: synthetic photos are optimistic; Pair C's real error table is the final word. Extend `selftest.py` or add `stress_test.py`.
- [ ] ✨ **A11. Future-feature spike: AI chat reports a dimension.** Prototype only, not wired into the app. Good for the roadmap slide.

## Status (update at each checkpoint)
- **Done:** A1, A2, A3, A4 (GO), A6, A7, sheet B support. Self-test passes.
- **Blocked:**
- **Next:** A5, the robustness pass, as Pair C's photo set arrives. A12/A13 are on hold.
