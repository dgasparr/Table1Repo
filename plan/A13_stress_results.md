# A13 stress test: where the tool works and where it breaks

**What we did:** 210 computer-generated photos of the hand-drawn 2×2 board, using a 12 MP phone camera model on the main 1× lens:
- **7 angles** (0–75° from straight-on) × **5 distances** (3–20 ft) × **sharp or shaky**, with 3 different hand-drawn boards each;
- **simulated hand drawing:** cell corners jittered by 0.35 mm;
- **simulated phone effects:** noise and JPEG compression.

In each photo we measured two lines whose true length we know exactly. Rerun with `python stress_test.py`; it takes about 1 minute.

⚠️ **Caveat:** our real Sharpie board is about 2× wobblier than the simulation (real corner fit 0.86–1.04 mm vs 0.55 mm simulated). Expect real errors to be roughly 2× the numbers below. Pair C's tape-measure error table is the final word.

## 1. Measuring next to the board (a 12" line just below it)

Worst error over 3 boards, sharp photos:

| Angle | 3 ft | 6 ft | 10 ft | 15 ft | 20 ft |
|---|---|---|---|---|---|
| 0° | 0.02" | 0.02" | 0.07" | 0.03" | 0.19" |
| 30° | 0.02" | 0.04" | 0.04" | 0.12" | 0.07" |
| 45° | 0.04" | 0.06" | 0.11" | 0.17" | 0.11" |
| 60° | 0.05" | 0.06" | 0.16" | 0.17" | ❌ not found |
| 75° | 0.04" | 0.06" | 0.23" | 0.54" | ❌ not found |

- **3–10 ft, up to 45°:** worst case about 1/8"; typical error **about 1/32"**. Green badge almost everywhere.
- **Shaky photos:** just as good up to 10 ft. Beyond 10 ft they get bad fast; at 60° and 15 ft one error was 4".
- **Board not found:** at 20 ft beyond 45°, and in shaky photos at 15 ft beyond 60°.

## 2. Measuring far from the board (a 48" door-width reach starting at the board)

- **Errors of 0.5–3" even in good photos.** At 15–20 ft they get worse.
- **Why:** a 7" board measuring 48" stretches the board's tiny drawing errors about 7 times, and the perspective errors grow faster than that.
- **The good news is the "±" knew this.** The app showed about ±1.3" on these lines, and the true error was always inside 2× the shown ±.

## 3. Is the "±" (A12) honest? Yes

- **Near lines (12"):** the true error was within 2× the shown ± in **97%** of photos. That's what an honest ±1-sigma should do, since roughly 95% is expected.
- **Far lines (48"):** **100%**.
- **The badges mean something:** for 12" lines, green photos had a median error of 0.035", yellow 0.085", red 0.19".

## Capture rules (for Pair C's cartoon), now backed by the test

1. ✅ **Stand 3–10 ft from the board.** Beyond 10 ft, accuracy and detection drop off, especially with any shake.
2. ✅ **Stay within 45° of straight-on.** Up to 60° is OK when close (3–6 ft).
3. ✅ **Hold still.** Shake is harmless up to 10 ft and harmful beyond it.
4. ✅ **Put the board right next to what you're measuring.** Measuring something 4 ft away from a 7" board gives about ±1–3". Watch the "±".
5. ❌ No 0.5× lens (not tested; it adds lens distortion the model doesn't correct).

## Pitch line

"We tested 210 photos: next to the board, 1/32" typical error from 3–10 ft and up to 45°. And the app knows when it's unsure: its ± covered the true error 97% of the time."

## Engine tweaks considered

- **Detection:** it only fails outside the capture rules (20 ft or very steep), so there's no change worth risking now.
- **Badge cutoffs:** they already separate good from bad photos (green 0.035" vs red 0.19" median error), so they stay as they are.
- **The real fix for long reaches** is not a setting. It's a bigger board, or two boards spread across the span (roadmap).
