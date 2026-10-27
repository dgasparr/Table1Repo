# Pair A — Detection & math

**Team:** Daniel + Benjamin

**Mission:** turn a photo into a trustworthy scale. Implement the real `measure.py` behind the frozen contract in [../ARCHITECTURE.md](../ARCHITECTURE.md).
**You own:** `measure.py`, `calcpad_markers.py`. **Don't edit:** `app.py`, `tests/`, `assets/`.
**Your input:** photos from Pair C in `tests/photos/`. **Your customer:** Pair B calls your functions.

## Block 1 → CP1 (~1:00)
- [ ] **A1. Push Benjamin's script.** Add `calcpad_markers.py` to the repo unchanged and push.
  *Done when:* it runs from the repo on Benjamin's synthetic test image.
- [ ] **A2. Real `detect()`.** Replace the stub body: detect IDs 0–3 (`DICT_4X4_50`, tolerant settings, sub-pixel corners), compute H with all detected corners, compute `rms_mm`, and set the grade (green < 1 mm, yellow 1–2, red > 2, none when not found). Board geometry: cell ½", marker 3", gap 1", ID 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right.
  *Done when:* `detect()` on the synthetic image returns `found=True`, 4 IDs, rms < 1 mm.
- [ ] **A3. `fmt_ft_in()`.** Output `4'-0 9/16"` style, rounded to 1/16". Handle under 1 ft (`0'-7 1/4"`) and inch rollover (11 31/32" → `1'-0"`).
  *Done when:* a few `assert` checks pass.
- [ ] **A4. First real photo.** Run `detect()` on Pair C's first phone photo of the drawn board.
  *Done when:* you can report found / not found at **CP1 (the go/no-go)**. If not found, try the detector parameters (adaptive threshold window, `minMarkerPerimeterRate`, `polygonalApproxAccuracyRate`) before giving up.

## Block 2 → CP2 (~2:30)
- [ ] **A5. Robustness pass.** Run `detect()` on every photo in `tests/photos/`. Print a table of file, found, ids, rms_mm, grade.
  *Done when:* at least 8 of 10 good-practice photos are found; failures are explained (too small, blur, angle, etc.).
- [ ] **A6. Partial boards.** If only 1–3 markers are found, still compute H from what was found, but lower the grade one level and say so in `message`.
- [ ] **A7. `draw_overlay()`.** Marker outlines in the grade color, with the ID labels drawn.
- [ ] **A8. Accuracy check.** On 2–3 photos, measure a known on-plane distance (the board's own outer edges, or a letter sheet) and compare it to the truth.
  *Done when:* the error is noted in your Status section.

## Block 3 → CP3 FREEZE (3:45)
- [ ] **A9. `area_mm2()` verified** on a letter sheet (8.5×11 in = 60,322 mm²).
- [ ] ✨ **A10. Rectified view helper** (`rectify(image, det) -> image`, top-down at about 4 px/mm). Only if Pair B wants it; agree on the signature at CP2.
- [ ] ✨ **A11. Future-feature spike: AI chat reports a dimension.** Prototype only, not wired into the app. Good for the roadmap slide.

## Status (update at each checkpoint)
- **Done:**
- **Blocked:**
- **Next:**
