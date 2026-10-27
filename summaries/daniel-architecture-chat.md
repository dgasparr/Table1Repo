# Summary — Daniel × Claude (feasibility, markers, architecture)

**Context:** hackathon, 6 people, started 11:25, pencils down 4:30 with a short lunch (about 4 h of real build time).
**Idea:** put known-size stickers on building elements (wall, pipe, door, column), photograph them, then ask a chatbot questions like "what's the width of the column next to the fire extinguisher?"

## Decisions / recommendations

1. **The MVP is feasible if kept tight:** one photo, sticker(s) on the same plane as the target, chat answers about width/height, and the measurement drawn on the image.
2. **Measurement accuracy is the risk, not the chat.** Vision LLM pixel coordinates are approximate, so every measurement gets drawn as an overlay that the user can check.
3. **Claude finds things, Python does the math.** Claude returns pixel coordinates through tools (`measure_line`, `measure_box`); Python converts them to mm using the sticker scale.
4. **Stickers are hand-drawn ArUco markers on engineering paper** (no printer available):
   - `DICT_4X4_50`, IDs 0 and 1. Each marker is a 6×6 cell grid; each cell is 5×5 squares (1"), so the marker is 6"×6".
   - Fill the cells solid with a Sharpie, not a ballpoint. Leave at least 1" of white margin. Measure the real outer size with a ruler.
   - **Fallback:** a solid black 4"×4" square detected as a 4-sided shape (less robust, no ID).
5. **Stack:** Python, OpenCV (`opencv-contrib-python`), Claude API (vision + tool use), Streamlit UI.
6. **Model usage (Claude Code):** Opus 5.5 for planning/architecture, Sonnet 5.5 for routine coding.

## Architecture (full detail in `ARCHITECTURE.md`)

- Modules: `core/` (shared dataclasses + config), `vision/` (markers, scale/homography, overlay), `agent/` (prompts, tools, chat loop), `pipeline.py`, `app.py`.
- **Contract:** `core/models.py` (`Marker`, `ScaleModel`, `Scene`, `Annotation`, `Answer`), frozen at 12:00.
- **Stubs first:** every module returns fake data in the agreed format by 12:15, so nobody blocks anyone.
- **Resize the image once** in `pipeline.analyze` (long edge ≤ 1568 px) and send that exact image to Claude, so coordinates line up.
- Branch per module; `main` must always run; secrets go in `.env`.

## Proposed roles

| Role | Count | Owns |
|---|---|---|
| Lead | (Daniel?) | `core/`, `pipeline.py`, `requirements.txt` |
| CV | 2 | `vision/markers.py`, `vision/scale.py`, `vision/overlay.py` |
| LLM | 2 | `agent/prompts.py`, `agent/chat.py`, `agent/tools.py` |
| UI | 1 | `app.py` (Streamlit) |
| Data/Demo | 1 | draw stickers, ~10 test photos with tape-measured ground truth, `eval.py`, pitch |

## Timeline

| Time | Milestone |
|---|---|
| 12:00 | Contract frozen; one hand-drawn marker detected on a phone photo |
| 12:15 | Stubs on `main`; app runs end to end on fake data |
| 1:45 | Real detection + scale; Claude tool loop working on its own |
| 2:30 | Real end-to-end |
| 3:15 | Eval table on ground-truth photos; fix the worst cases |
| 3:45 | Feature freeze |
| 4:00–4:30 | Rehearse the demo, record a backup video |

## Risks / known limits

- Measurements are only valid **on the sticker's plane**.
- A hand-drawn marker may fail detection if streaky or too small. **Test this first** (~15 min).
- Claude's pixel locations are approximate. **Mitigation:** overlay; stretch goal is click-two-points.

## Stretch goals

Cross-check scale across multiple stickers, click-to-measure, multi-photo / 3D, area and counting tools, FastAPI/mobile front end.

## Open items

- [ ] Confirm `opencv-contrib-python` install / Python env.
- [ ] Write the marker-detection test script + ASCII patterns for IDs 0 and 1 (offered, not done yet).
- [ ] Scaffold the folders, `core/models.py` and the stubs (offered, not done yet).
- [ ] Assign names to roles.
