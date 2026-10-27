# Team playbook — how we work until 4:30

Read this first (2 min). Then open your pair's file: [PAIR_A.md](PAIR_A.md) · [PAIR_B.md](PAIR_B.md) · [PAIR_C.md](PAIR_C.md)

Background: [../summaries/CONSOLIDATED.md](../summaries/CONSOLIDATED.md) (decisions) · [../ARCHITECTURE.md](../ARCHITECTURE.md) (contract)

## The pairs

| Pair | Who | Mission | Uses Claude for |
|---|---|---|---|
| **A: Detection & math** | Daniel + Benjamin | Photo in → scale out (`measure.py`) | Wrapping Benjamin's script, tuning detection, ft-in formatting |
| **B: UI** | Yang + David | Streamlit app: upload, click, show length | All of `app.py` |
| **C: Target, test rig, demo** | Tuan + Ryan | Board, photos, answer key, cartoon, demo | Marker generator, cartoon image, error table, demo script |

**All three pairs use Claude.** Pair C is about half field work (drawing, measuring, photos) and half desk work (generator script, cartoon, merging, demo).

## Working with Claude (every pair)
1. Clone the repo, open it in VS Code, start Claude Code.
2. First prompt: **"Read plan/README.md, plan/PAIR_X.md and ARCHITECTURE.md. We are Pair X. Do step X1."**
3. Use Sonnet 5.5 for coding (`/model`). Switch to Opus only if you're stuck.
4. One step at a time. Tick the box in your PAIR file when the step's **Done when** is true.

## Rules that keep us out of each other's way
- **Only edit files your pair owns** (see ARCHITECTURE.md). If you need a change in someone else's file, ask them.
- **`measure.py` signatures are frozen.** Pair B codes against them today using the stub.
- **Everyone works on `main`, with no branches.** Commit small and often.
- **Before every push:** `git pull --rebase`, then `git push`.
- **Only push code that runs.** `streamlit run app.py` must still start after your push.
- Pair A keeps the stub in `measure.py` until real detection works on a real photo, then swaps it in.
- Photos go in `tests/photos/` (Pair C). Everyone may *read* them.

## Setup (everyone, 5 min)
Requires **Python 3.12** installed.
```bat
git clone https://github.com/dgasparr/Table1Repo.git
cd Table1Repo
setup_venv.bat
venv\Scripts\activate
```
- `setup_venv.bat`: pick your Python 3.12 `python.exe` in the dialog. It creates `.\venv` and ends by printing `OK ... aruco: True`.
- `venv\Scripts\activate`: run this in every new terminal.
Dependencies live in `pyproject.toml`. To add one, ask Pair C, then everyone re-runs `pip install -e .`

## Checkpoints

At each checkpoint **every pair stops and meets for 5 minutes**:
1. Each pair: update the **Status** section at the bottom of your PAIR file (done / blocked / next).
2. Each pair: `git add` your files, `git commit`, `git pull --rebase`, `git push`.
3. Everyone: `git pull`. One laptop runs `streamlit run app.py` on the big screen.
4. 3-minute stand-up: read the 3 Status sections. **Decide what's in or out for the next block.** Daniel makes the final call.

| CP | Target time | The whole team has… | Go / no-go question |
|---|---|---|---|
| **CP1** | ~1:00 (before lunch) | App running on the stub; board drawn; first real photo detected | **Does the hand-drawn board detect?** If not: retune, redraw bigger, or fall back to a single 6" marker |
| **CP2** | ~2:30 | **Real end to end:** phone photo → click → ft-in length + badge | Is the accuracy good enough? Add area or not? |
| **CP3** | 3:45 **FREEZE** | Error table done, cartoon in the app, demo script written | Nothing new after this, only fixes |
| **CP4** | 4:15 | Demo rehearsed twice, backup video recorded | — |

If a pair finishes early: help the pair with the most open boxes, or take the next ✨ stretch step in your file.
