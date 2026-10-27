# Pair C — Target, test rig, integration, demo

**Team:** Tuan + Ryan

**Mission:** give Pairs A and B real inputs fast, prove accuracy with numbers, and own the demo.
**You own:** `tests/`, `assets/`, `tools/`, `pyproject.toml`, `setup_venv.bat`, `.gitignore`, and the demo.
**Don't edit:** `measure.py`, `app.py`.

Split the pair: **C-field** (drawing, measuring, photos) and **C-desk** (Claude: scripts, cartoon, error table, demo). Swap if one side runs ahead.

## Block 1 → CP1 (~1:00)
- [ ] **C1 (desk). Repo check.** Clone, run the setup in README, and confirm `setup_venv.bat` works (it prints OK with aruco: True).
- [ ] **C2 (desk). Marker generator.** `tools/make_markers.py`: render `DICT_4X4_50` IDs 0–3 with `cv2.aruco.generateImageMarker` as large 6×6 grids with row/column numbers, plus the full 2×2 board preview (ID 0 top-left, 1 top-right, 2 bottom-left, 3 bottom-right). Show them on screen for C-field to copy.
  ⚠️ **Do not copy the ASCII patterns from the summaries** (the paste corrupted them).
- [ ] **C3 (field). Draw the board** on the 1" / ⅛" pad: cell ½" (4 small squares), marker 3", gap 1", board 7"×7", ¾" margin. Use a black Sharpie, fill cells fully, keep the whites clean, never mirror a marker. Measure the outer edges with a ruler and write down the actual size. **Draw a spare** if time allows.
- [ ] **C4 (field). First photo → Pair A.** Tape the board flat on a wall, take 1 photo straight-on and 1 at about 30°, from about 5 ft, on the 1× lens. Put them in `tests/photos/` and push. **This is the CP1 go/no-go.**
- [ ] **C5 (field). Answer key.** Tape-measure 5 targets **on the same wall as the board**: board edge, a letter sheet, a door width, a whiteboard, a wall feature. Write `tests/answer_key.csv` with columns `target,true_in,notes`.

## Block 2 → CP2 (~2:30)
- [ ] **C6 (field). Photo set**, named like `door_30deg_6ft.jpg`: straight-on, 30°, 60°, board small in frame (about 12 ft), board near the edge, plus 1 deliberately bad one (0.5× lens or blurry) to show the red badge. Aim for about 10. iPhone: Formats → Most Compatible.
- [ ] **C7 (desk). Capture-rules cartoon** → `assets/capture_rules.png` for the in-app help. Do/don't panels:
  - ✅ 3–10 ft away · ✅ within 45° · ✅ whole board in frame · ✅ paper flat · ✅ 1× lens
  - ❌ 0.5× lens · ❌ board at the edge or cut off · ❌ steep angle · ❌ curled paper or glare · ❌ measuring off the board's surface

  Either have Claude draw it (matplotlib or SVG to PNG), or hand-draw it and photograph it. Keep it simple and readable on a phone.
- [ ] **C8 (desk). Checkpoint run.** At each checkpoint, `git pull` and run the app on the big screen with the newest photos.

## Block 3 → CP3 FREEZE (3:45)
- [ ] **C9 (both). Error table.** Use the app to measure every answer-key target in every photo. Fill `tests/error_table.csv` with `photo,target,true_in,app_in,error_in,error_pct,grade`. Pull out the headline numbers: median error, worst case and why.
- [ ] **C10 (desk). Demo script** in `plan/DEMO.md` (5 min): problem → capture rules (cartoon) → live phone photo at an angle → measure the door in ft-in → badge → error table → limits (single plane) → roadmap (AI chat reporting dimensions, off-plane measurement, multi-photo mosaic, LiDAR, printed ChArUco target).
- [ ] **C11. Roadmap slide**, 1 slide using the future features from CONSOLIDATED.md.

## Block 4 → CP4 (4:15)
- [ ] **C12.** Rehearse the demo twice with the whole team; record a backup screen video of the full flow.

## Status (update at each checkpoint)
- **Done:**
- **Blocked:**
- **Next:**
