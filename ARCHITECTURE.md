# Architecture — Site Photo Measurement Tool (MVP)

Decisions: see `summaries/CONSOLIDATED.md`. Team process: see `plan/README.md`.

**MVP:** upload a photo (from a phone or laptop) showing the hand-drawn 2×2 ArUco board → the user clicks two points on the same flat surface → the app shows the real length in ft-in, plus a fit-quality badge.

## Data flow

```
photo (phone/laptop upload)
   │
   ▼
measure.detect(image) ──► Detection  (marker corners, H: px → mm, rms_mm, grade)
   │                                   │
   ▼                                   ▼
app.py shows photo + outline + badge   user clicks p1, p2 (full-res px)
                                       │
                                       ▼
                         measure.distance_mm(H, p1, p2) → fmt_ft_in() → shown on screen
```

## Files and owners

| File | Owner | Purpose |
|---|---|---|
| `measure.py` | Pair A | **The contract.** Detection + math. No Streamlit imports |
| `calcpad_markers.py` | Pair A (Benjamin) | Original script; `measure.py` wraps it |
| `app.py` | Pair B | Streamlit UI. No OpenCV math here; call `measure.py` only |
| `assets/capture_rules.png` | Pair C | Do/don't cartoon shown inside the app |
| `tools/make_markers.py` | Pair C | Renders IDs 0–3 large to copy onto the pad |
| `tests/photos/`, `tests/answer_key.csv`, `tests/error_table.csv` | Pair C | Test rig and results |
| `pyproject.toml`, `setup_venv.bat`, `.gitignore` | Pair C | Ask before adding a dependency |

## The contract: `measure.py`

Signatures are **frozen**. Changing one requires telling all pairs at a checkpoint.

```python
@dataclass
class Detection:
    found: bool                  # at least one marker found and H computed
    ids: list[int]               # marker IDs found (subset of 0..3)
    corners_px: list[np.ndarray] # one (4,2) array per marker, full-res px
    H: np.ndarray | None         # 3x3, full-res image px -> board-plane mm
    rms_mm: float | None         # corner-fit residual
    grade: str                   # "green" (<1 mm) | "yellow" (1–2) | "red" (>2) | "none"
    message: str                 # human-readable status / warning

def detect(image_bgr: np.ndarray) -> Detection
def distance_mm(H, p1: tuple[float, float], p2: tuple[float, float]) -> float
def area_mm2(H, points: list[tuple[float, float]]) -> float
def fmt_ft_in(mm: float, denom: int = 16) -> str   # 1234.0 -> 4'-0 9/16"
def draw_overlay(image_bgr, det: Detection) -> np.ndarray  # marker outlines + IDs
```

**Coordinate rule:** every point passed to `measure.py` is in **full-resolution image pixels**. `app.py` displays a resized copy and converts each click back to full-res with `x_full = x_click * (full_width / display_width)`.

## Board spec (do not change)

`DICT_4X4_50`, IDs 0 (top-left), 1 (top-right), 2 (bottom-left), 3 (bottom-right). Cell ½" → marker 3"×3" (6×6 cells including the black border), gap 1", board 7"×7". Drawn on the 1" / ⅛" calc pad with a black Sharpie.

## Known limit

Measurements are valid **only on the board's plane**. Say this in the app and the demo.
