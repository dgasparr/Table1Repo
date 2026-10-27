# Pair B — UI (Streamlit)

**Team:** Yang + David

**Mission:** an app an engineer can use: upload a photo, click two points, read the length in ft-in, and know whether to trust it.
**You own:** `app.py`. **Don't edit:** `measure.py` (it's Pair A's; call it, don't change it), `tests/`, `assets/`.
**Your input:** `measure.py` (a stub today, real after CP1) and `assets/capture_rules.png` from Pair C.

**Rule:** no OpenCV math in `app.py`. Only call `measure.detect`, `distance_mm`, `area_mm2`, `fmt_ft_in`, `draw_overlay`.

## Block 1 → CP1 (~1:00), all on the stub
- [ ] **B1. Skeleton.** Title, a one-line "how it works", and `st.file_uploader` (jpg/jpeg/png). Decode to a BGR numpy array.
  *Done when:* an uploaded photo is displayed.
- [ ] **B2. Detect + overlay.** Call `detect()`, show `draw_overlay()`, and show the badge (🟢/🟡/🔴 + `rms_mm` + `message`). If `found=False`, show a clear error and a link to the capture rules.
- [ ] **B3. Click two points.** Use `streamlit-image-coordinates` on a **resized** display copy (about 1200 px wide). Convert clicks to full-res: `x_full = x * full_w / disp_w`. Keep the points in `st.session_state`; the third click starts a new line. Add a "Clear" button.
  *Done when:* two clicks draw a line on the image.
- [ ] **B4. Show the length.** `distance_mm(det.H, p1, p2)` → `fmt_ft_in()`, shown large next to the line. Add a units toggle: ft-in / mm / decimal inches.
- [ ] **B5. Phone test.** Run `streamlit run app.py --server.address 0.0.0.0`, then open `http://<laptop-IP>:8501` on a phone and upload with "Take Photo". If the venue Wi-Fi blocks it, use a phone hotspot.
  *Done when:* a phone photo arrives in the app. Report the steps at CP1.

## Block 2 → CP2 (~2:30), on real `detect()`
- [ ] **B6. Swap to real.** Once Pair A swaps in real detection (around CP1), `git pull` and test with Pair C's photos. Fix anything that breaks (big phone images, EXIF rotation: apply `ImageOps.exif_transpose` before converting to BGR).
- [ ] **B7. Single-plane warning.** A permanent caption: "Only measure points on the same flat surface as the board."
- [ ] **B8. Capture-rules help.** An expander or sidebar showing `assets/capture_rules.png` (show placeholder text until Pair C delivers it).
- [ ] **B9. Measurement list.** Keep each measurement (label, value) in a small table on the page.

## Block 3 → CP3 FREEZE (3:45)
- [ ] **B10. Area mode** (only if decided at CP2): a mode switch, click N points, a "Close shape" button, `area_mm2()` → ft² and m².
- [ ] ✨ **B11. Download** the annotated image (`st.download_button`).
- [ ] ✨ **B12. Rectified-view toggle**, if Pair A ships `rectify()`.
- [ ] **B13. Polish for the demo:** big fonts and a clean layout; remove debug output.

## Status (update at each checkpoint)
- **Done:**
- **Blocked:**
- **Next:**
