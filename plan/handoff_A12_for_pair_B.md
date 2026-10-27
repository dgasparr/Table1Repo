# Handoff from Pair A → Pair B: A12 "±" uncertainty on lengths

**Status:** ✅ **pushed to `main`.** Run `git pull`, then wire it in. Tested on the real photos: the board's 7" edge reads `0'-7" ± 1/16"`.
Nothing existing changes: `distance_mm`, `area_mm2`, `fmt_ft_in`, `draw_overlay` and `detect` stay the same.

## Two new functions in `measure.py`

```python
def distance_with_uncertainty(det: Detection, p1, p2) -> tuple[float, float, str]:
    """Returns (length_mm, uncertainty_mm, warning).
    uncertainty_mm: 1-sigma from marker-corner noise (click error not included).
    warning: "" or short text, e.g. points far from the board -> less accurate."""

def fmt_pm(unc_mm: float) -> str:
    """'± 1/16"' style, rounded to 1/16"; '± <1/16"' when it rounds to zero."""
```

Points are the same as before: `(x, y)` tuples in **full-resolution** image pixels.

## What to change in `app.py` (about 5 lines)

1. Where a length is completed (`len(pts) == 2`), replace
   `mm = measure.distance_mm(det.H, pts[0], pts[1])`
   with
   `mm, unc, warn = measure.distance_with_uncertainty(det, pts[0], pts[1])`
   and store `"unc": unc, "warn": warn` in the measurement dict.
   It takes about 50 ms. You already call it once per completed line, which is right; don't call it on every rerun.
2. **Big result:** show `f"{fmt_length(mm, units)} {measure.fmt_pm(unc)}"`, e.g. `8'-4 1/2" ± 1/16"`.
   In mm or decimal-inch units, show `± {unc:.1f} mm` or `± {unc/25.4:.2f}"` instead.
3. If `warn` isn't empty, show it as a caption under the result.
4. **Measurements table:** add a `±` column. Optional: put the ± in the on-image label.
5. **Area mode:** no change; no ± for area.

## Why

Engineers don't trust bare numbers. "8'-4 1/2" ± 1/16"" reads like a surveyor's tolerance, and it gets bigger automatically when the photo is blurry, the board is small or the points are far from the board.

## Also from the end-to-end check (separate, optional)

Portrait photos render only 450 px wide (`VIEW_H = 600` caps them), so one screen pixel ≈ 1.6–3 mm at the board, and click error is the biggest error source. Cheap fix: raise the default height for portrait photos (e.g. `VIEW_H = 900`). ✨ Stretch: a zoom/crop view around the board for precise clicks, mapping crop px back to full-res px.
