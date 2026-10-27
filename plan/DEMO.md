# Demo script (5 min)

**Setup before going on:**
- Laptop runs `streamlit run app.py --server.address 0.0.0.0 --server.headless true`. The phone has the Network URL open, on a hotspot if venue Wi-Fi blocks it.
- Board (sheet A) taped flat on a wall, **right next to** a measurable object (window frame, outlet plate, sign, door edge), with its true size on a sticky note.
- Backups in `tests/photos/`: a known-good photo, plus the backup screen recording.
- App units set to **ft-in**.

| Time | Who | Say | Do |
|---|---|---|---|
| 0:00 | Speaker 1 | "Site dimensions get lost: you leave the site, the ceiling gets closed up, and the RFI comes back asking how wide that opening was." | Title slide |
| 0:30 | Speaker 1 | "Our fix: a hand-drawn sticker and a phone photo. Capture now, measure later, from any browser." | Hold up the drawn board |
| 0:50 | Speaker 2 | "The board is four ArUco markers drawn with a Sharpie on a calc pad. The app finds them and corrects for perspective, so the photo can be taken at an angle." | Show the cartoon in the app sidebar |
| 1:20 | Speaker 2 | "Here's the rule card: where to stand, what angle, what to avoid." | Point at DO/DON'T |
| 1:40 | Speaker 3 | **Live:** "I'll take a photo at an angle right now." | Phone → Take Photo → upload. Badge goes 🟢/🟡 |
| 2:10 | Speaker 3 | "Green means the board fit is good. Click two points…" | Click the object's edges → big ft-in readout **with ±** |
| 2:40 | Speaker 3 | "…8'-4 1/2 plus or minus 1/16. The plus-or-minus is the point: the app tells you how far to trust it." | Show the true value on the sticky note |
| 3:00 | Speaker 3 | "Watch what happens if I reach far from the board." | Click a far point → large ± + warning |
| 3:20 | Speaker 4 | "On our real photos, the board's known 7-inch edge reads 7 inches, on a wall and on a table at a steep angle." | Show image01/image02 in the app |
| 3:50 | Speaker 4 | "Limits: it measures one flat surface, the one the board is on. And the ± grows when you reach far from the board." | |
| 4:15 | Speaker 5 | Roadmap (below) | Roadmap slide |
| 4:50 | All | "Questions?" | |

**If the live photo fails:** "That's what the rule card is for." Show the red badge or the message, then upload the backup photo from `tests/photos/`. Never debug on stage.

## Pitch lines to reuse
- "Capture now, measure later: any phone, no app install, no LiDAR."
- "A Sharpie and a calc pad are the whole hardware budget."

## Roadmap slide (C11)

**Where FieldScale goes next**
1. **Ask it, don't click it:** an AI chat that finds "the column next to the fire extinguisher" and measures it with the same math.
2. **Beyond one wall:** off-plane measurement (heights, depths) from one photo using vanishing lines, plus multi-photo stitching for long walls.
3. **Better targets:** a printed ChArUco card or magnetic plate; two boards spread across a span to kill the long-reach error.
4. **Pro devices:** LiDAR on iPhone/iPad Pro as an independent cross-check.
5. **Field validation:** a tape-measure error study on real sites before anyone relies on it.
6. **Workflow:** project folders, audit trail (photo + calibration + clicks), annotated exports for field reports and RFIs.
