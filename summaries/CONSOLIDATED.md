# Consolidated plan — Site Photo Measurement Tool

Sources: Benjamin, Yang, Tuan, David, Ryan, Daniel (+ Claude). The sections follow **Yang's 5 categories**.
Legend: ✅ = decided · 🔜 = future feature (roadmap slide)

---

## Decisions (locked)

| # | Decision | Future feature |
|---|---|---|
| 1 | ✅ **Click to measure.** The user clicks points on the photo | 🔜 Give the image to an AI chat to report dimensions |
| 2 | ✅ **ArUco markers**, hand-drawn on the calc pad | 🔜 Printed ChArUco target |
| 3 | ✅ **Streamlit**, usable from a phone (see section 3) | 🔜 FastAPI + web canvas app |
| 4 | ✅ **Ban the 0.5× ultra-wide lens.** No lens undistortion in the MVP | 🔜 Camera calibration |
| 5 | ✅ **Length first**; area if time allows | 🔜 Elevation, export |
| 6 | ✅ **Single plane only** | 🔜 Off-plane measurement (Benjamin's research) |
| 7 | ✅ **Cartoon of the capture rules** (do / don't image), shown **inside the app** as user help | — |
| 8 | ✅ **Benjamin's 2×2 ArUco GridBoard** (IDs 0–3, 7"×7") | — |
| 9 | ✅ **Yang's 3 pairs**. Step-by-step plans are in `plan/` | — |

---

## 1. Basic assumptions

- **Single plane:** only measure things on the same flat surface as the target. Say this on screen and in the demo.
- A homography from the marker corners maps image pixels to real units on that plane.
- Validate against tape-measured ground truth; show an error table in the demo.

**Capture rules** (to show as the cartoon, decision 7):
1. Stand 3–10 ft from the target.
2. Stay within about 45° of straight-on.
3. Keep the whole target in frame, not within about 5% of the edge.
4. Keep the paper flat (tape all 4 edges) and avoid glare.
5. Use the main 1× lens; **never 0.5×**.
6. iPhone: Settings → Camera → Formats → **Most Compatible** (JPG, not HEIC).

---

## 2. Good-to-have features (in build order)

| # | Feature | Call |
|---|---|---|
| 1 | Two-click length, shown in ft-in | **MVP** |
| 2 | Detected target outline drawn on the photo | **MVP** (trivial) |
| 3 | **Fit-quality badge** (explained below) | **MVP** (already in Benjamin's code) |
| 4 | Polygon area | If time allows |
| 5 | Rectified (straight-on) view | Stretch (already in Benjamin's code) |
| 6 | Elevation, EXIF/GPS, export annotated image | Stretch |
| 🔜 | AI chat, off-plane, multi-photo mosaic, photo-to-photo matching, LiDAR, lens calibration | Roadmap slide |

**What item 3 is (the fit-quality badge):** the board has 16 marker corners at exactly known positions. After computing the homography, the code checks how far each detected corner lands from where it *should* be, in mm. The RMS of those misses is a free self-check on the whole photo:
- 🟢 under 1 mm: trust it.
- 🟡 1–2 mm: usable, take care.
- 🔴 over 2 mm: retake the photo. Likely causes are blur, curled paper, a marker drawn badly, or too steep an angle.

It is one number already computed by `calcpad_markers.py`, so it just needs a colored label next to each measurement. Engineers will want to see it.

---

## 3. Frontend assumptions

- Upload button → show photo → click two points → line plus value.
- **Units: ft-in `xx'-xx"`** by default; toggle to mm / decimal inches.
- Show the detected target outline and the fit badge.
- Resize the photo for display and keep the scale factor, so clicks map back to full-resolution pixels.

**Can we use the phone with Streamlit? Yes:**
1. Run `streamlit run app.py --server.address 0.0.0.0` on a laptop.
2. On the phone (same Wi-Fi), open `http://<laptop-IP>:8501`. Find the IP with `ipconfig`.
3. Tap Upload. iOS and Android both offer **"Take Photo"** directly from the upload button, which works over plain HTTP.

Watch-outs:
- Corporate or venue Wi-Fi often blocks device-to-device traffic. If the phone can't connect, **turn on a phone hotspot and join the laptop to it**, or use `ngrok http 8501`.
- Allow Python through the Windows Firewall when Windows asks.
- `st.camera_input` (a live camera view inside the page) needs HTTPS, so use the upload button instead.
- Clicking precise points on a small phone screen is clumsy. **Demo flow: capture on the phone, measure on the laptop**, which matches Ryan's "capture now, measure later".

---

## 4. Technology

**Stack:** Python 3.11+, `opencv-contrib-python`, `streamlit`, `streamlit-image-coordinates`, `numpy`, `pillow`.

**Target (✅ decided):** Benjamin's **2×2 ArUco GridBoard**: `DICT_4X4_50` IDs 0–3, 3" markers, 1" gap, 7"×7" board, drawn on the 1" / ⅛" pad. It gives 16 corners, which averages out hand-drawing error and powers the fit badge, and the code already exists. The fallback is a single 6" marker.
- ⚠️ Generate the marker images on a laptop (`cv2.aruco.generateImageMarker`) and copy them from the screen. **Do not** copy the ASCII patterns from the pasted summary; characters were lost in the paste.
- Use a black Sharpie, never mirror or rotate a marker, and keep the white margins clean.

**Core code = Benjamin's `calcpad_markers.py`.** Wrap it in importable functions:
```python
detect(image) -> Detection        # corners, ids, H (px -> mm), rms_mm, overlay
distance_mm(H, p1, p2) -> float
area_mm2(H, points) -> float      # if time allows
fmt_ft_in(mm) -> str              # 1234 mm -> 4'-0 9/16"
```
The UI builds against a stub that returns the identity matrix as `H` from minute one.

---

## 5. Team split (✅ Yang's 3 pairs; step-by-step plans in `plan/`)

| Pair | People | Owns | Done when |
|---|---|---|---|
| **A: Detection & math** | Benjamin + 1 | `measure.py` (wraps Benjamin's script), ft-in formatting, fit badge, then area | `detect()` works on 8 of 10 real photos |
| **B: UI** | 2 | `app.py`: upload, click, line, outline, badge, units, phone access | Works on the stub, then on real `detect()` |
| **C: Target, test rig, demo** | 2 | Draw the board (+ a spare), capture-rules cartoon, tape-measured answer key, photo set (straight-on / 30° / 60° / small / near the edge), error table, demo script, roadmap slide | Error table filled in; demo rehearsed |

| Time | Milestone |
|---|---|
| 1:00 | Start. Benjamin pushes `calcpad_markers.py`; Pair C starts drawing. Lunch at desks, staggered |
| **1:45 CP1** | Drawn board detected on a real phone photo (go/no-go); UI running on the stub |
| **2:45 CP2** | **Real end to end:** phone photo → click → ft-in length + badge |
| 3:15 | Error table done; fix the worst cases; area only if well ahead |
| **3:45 CP3** | **Feature freeze** |
| **4:15 CP4** | Rehearsed twice, backup video recorded |

## Demo story
1. Problem: site dimensions are lost after the visit or once things are covered up.
2. Show the capture-rules cartoon.
3. Live: board on a wall → phone photo at an angle → upload → measure the door width in ft-in → fit badge.
4. Error table against the tape measure.
5. Honest limit: single plane only.
6. Roadmap: AI chat reporting dimensions, off-plane measurement, multi-photo mosaic, LiDAR, printed ChArUco target.
