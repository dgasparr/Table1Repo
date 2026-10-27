"""Streamlit UI. Owner: Pair B (Yang + David).

Rule: no OpenCV math here. Everything geometric goes through measure.py:
    detect, distance_mm, area_mm2, fmt_ft_in, draw_overlay
Every point handed to measure.py is in FULL-RESOLUTION image pixels.
"""
from __future__ import annotations

import html
import io
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
from streamlit_image_coordinates import streamlit_image_coordinates

import measure

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
# On-screen viewing box. Every photo is shown inside this frame regardless of
# its pixel size (landscape fills the width, portrait fills the height).
VIEW_W = 900                  # CSS px, default; adjustable in the sidebar
VIEW_H = 900                  # portrait photos fill this height
# Zoom loupe: a magnified crop around a rough click, for precise placement.
LOUPE_W = 420                 # CSS px on screen
LOUPE_WINDOWS = [150, 300, 600]   # crop size in full-res px (smaller = finer)
# Data copies sent to the browser are 2x their on-screen size so high-DPI
# screens stay sharp. Clicks are always scaled back to full-res.
ROOT = Path(__file__).parent
CAPTURE_RULES = ROOT / "assets" / "capture_rules.png"
LOGO = ROOT / "Smartphone AR Room Measurement Scanner-logo.png"
TUTORIAL = ROOT / "Tutorial Diagram.png"
PLANE_WARNING = "Only measure points on the same flat surface as the board."
HOW_IT_WORKS = (
    "Tape the hand-drawn marker board flat on the surface, take a photo, "
    "upload it, click two points on that same surface, read the length."
)

GRADE_ICON = {"green": "🟢", "yellow": "🟡", "red": "🔴", "none": "⚪"}
LINE_COLORS = ["#ff2d55", "#ff9500", "#5ac8fa", "#ffcc00", "#af52de", "#34c759"]

@st.cache_data(show_spinner=False)
def load_asset(path: str, max_w: int = 1600, transparent: bool = True) -> Image.Image | None:
    """Load a PNG. With transparent=True the near-white background is removed so
    an illustration sits cleanly on the dark theme. Line-art diagrams with black
    strokes should keep their white background (transparent=False)."""
    f = Path(path)
    if not f.exists():
        return None
    img = Image.open(f).convert("RGBA")
    if img.width > max_w:
        img = img.resize((max_w, round(img.height * max_w / img.width)), Image.LANCZOS)
    if not transparent:
        return img
    a = np.asarray(img).astype(np.int16)
    lightness = a[:, :, :3].min(axis=2)                  # 255 = pure white
    alpha = np.clip((250 - lightness) * 255 / 20, 0, 255)   # fade out 230..250
    a[:, :, 3] = np.minimum(a[:, :, 3], alpha)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def current_theme() -> str:
    try:
        return st.context.theme.type            # "light" | "dark"
    except Exception:
        return "light"


def set_theme(base: str) -> None:
    """Switch the Streamlit theme at runtime (uses a private config hook)."""
    try:
        st._config.set_option("theme.base", base)
    except Exception:
        pass


logo_img = load_asset(str(LOGO))
st.set_page_config(
    page_title="Site Photo Measure",
    page_icon=logo_img if logo_img is not None else "📐",
    layout="wide",
)
if logo_img is not None:
    st.logo(logo_img, size="large")

st.markdown(
    """
    <style>
      .big-result { font-size: 3.2rem; font-weight: 700; line-height: 1.1; margin: 0.2rem 0; }
      .sub-result { font-size: 1.1rem; opacity: 0.65; }
      .pm { font-size: 1.6rem; font-weight: 500; opacity: 0.6; white-space: nowrap; }
      .badge { font-size: 1.3rem; font-weight: 600; }
      .app-title { font-size: 2.4rem; font-weight: 700; line-height: 1.1; margin: 0; }
      .app-sub { font-size: 1.05rem; opacity: 0.75; margin-top: 0.3rem; }
      div[data-testid="stFileUploader"] label { font-size: 1.1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("image_key", None)      # identifies the current upload
    ss.setdefault("bgr", None)            # full-res BGR array
    ss.setdefault("det", None)            # measure.Detection
    ss.setdefault("points", [])           # in-progress clicks, full-res (x, y)
    ss.setdefault("measurements", [])     # dicts: label, kind, mm/mm2, points
    ss.setdefault("last_click", None)     # dedupe the component's repeated value
    ss.setdefault("click_nonce", 0)       # bump to reset the click component
    ss.setdefault("pending", None)        # rough click awaiting loupe refinement
    ss.setdefault("last_loupe_click", None)
    ss.setdefault("loupe_nonce", 0)


def _clear_pending() -> None:
    ss = st.session_state
    ss.pending = None
    ss.last_loupe_click = None
    ss.loupe_nonce += 1


def _reset_for_new_image() -> None:
    ss = st.session_state
    ss.points = []
    ss.measurements = []
    ss.last_click = None
    ss.click_nonce += 1
    _clear_pending()


def _clear_points() -> None:
    st.session_state.points = []
    st.session_state.last_click = None
    st.session_state.click_nonce += 1
    _clear_pending()


_init_state()

# ----------------------------------------------------------------------------
# Helpers (image IO and drawing only; no measurement math)
# ----------------------------------------------------------------------------
def load_bgr(uploaded) -> np.ndarray:
    """Decode an upload to a full-res BGR array, honouring EXIF rotation."""
    img = Image.open(uploaded)
    img = ImageOps.exif_transpose(img).convert("RGB")
    rgb = np.asarray(img)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def bgr_to_pil(bgr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.ascontiguousarray(bgr[:, :, ::-1]))


def fmt_length(mm: float, units: str) -> str:
    if units == "ft-in":
        return measure.fmt_ft_in(mm)
    if units == "mm":
        return f"{mm:,.1f} mm"
    return f'{mm / 25.4:,.2f}"'


def fmt_pm_units(unc_mm: float | None, units: str) -> str:
    """'± 1/16"' in ft-in; '± 0.8 mm' / '± 0.03"' in the other units."""
    if unc_mm is None:
        return ""
    if units == "ft-in" and hasattr(measure, "fmt_pm"):
        return measure.fmt_pm(unc_mm)
    if not np.isfinite(unc_mm):
        return "± ?"
    if units == "mm":
        return f"± {unc_mm:.1f} mm"
    return f'± {unc_mm / 25.4:.2f}"'


def fmt_area(mm2: float) -> str:
    ft2 = mm2 / 92_903.04
    m2 = mm2 / 1_000_000.0
    return f"{ft2:,.2f} ft²  ·  {m2:,.3f} m²"


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # old Pillow
        return ImageFont.load_default()


def _label(draw: ImageDraw.ImageDraw, xy, text: str, color: str, font) -> None:
    x, y = xy
    l, t, r, b = draw.textbbox((x, y), text, font=font)
    pad = max(2, font.size // 6)
    draw.rectangle((l - pad, t - pad, r + pad, b + pad), fill="black")
    draw.text((x, y), text, fill=color, font=font)


def draw_annotations(
    img: Image.Image,
    scale: float,
    measurements: list[dict],
    points: list[tuple[float, float]],
    units: str,
    offset: tuple[float, float] = (0.0, 0.0),
    marker_scale: float = 1.0,
) -> Image.Image:
    """Draw finished measurements and in-progress points on a copy of img.

    scale = img_width / full_res_width (points are stored full-res).
    offset = full-res (x, y) of img's top-left corner, for crops.
    Marker sizes are relative to the image width, so they look the same on the
    screen copy and on the full-res download.
    """
    out = img.copy()
    d = ImageDraw.Draw(out)
    W = out.width
    w = max(2, round(W / 600 * max(1.0, marker_scale / 2)))   # stroke
    r = max(6, round(W / 160 * marker_scale))                 # crosshair ring radius
    font = _font(max(16, round(W / 55 * marker_scale)))

    def s(p):
        return ((p[0] - offset[0]) * scale, (p[1] - offset[1]) * scale)

    def crosshair(p, color, halo=False):
        x, y = p
        if halo:  # dark outline so a white marker stays visible on light surfaces
            d.ellipse((x - r - 1, y - r - 1, x + r + 1, y + r + 1), outline="black", width=w + 2)
        d.ellipse((x - r, y - r, x + r, y + r), outline=color, width=w)
        gap = r // 3
        d.line((x - r - gap, y, x - gap, y), fill=color, width=w)
        d.line((x + gap, y, x + r + gap, y), fill=color, width=w)
        d.line((x, y - r - gap, x, y - gap), fill=color, width=w)
        d.line((x, y + gap, x, y + r + gap), fill=color, width=w)
        d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=color)   # exact centre

    for i, m in enumerate(measurements):
        color = LINE_COLORS[i % len(LINE_COLORS)]
        pts = [s(p) for p in m["points"]]
        if m["kind"] == "length":
            d.line(pts, fill=color, width=w)
            mid = ((pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2)
            text = f'{m["label"]}: {fmt_length(m["mm"], units)}'
            if m.get("unc") is not None:
                text += " " + fmt_pm_units(m["unc"], units)
        else:
            d.polygon(pts, outline=color, width=w)
            mid = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
            text = f'{m["label"]}: {fmt_area(m["mm2"])}'
        for p in pts:
            crosshair(p, color)
        _label(d, (mid[0] + r, mid[1] + r), text, color, font)

    # in-progress points
    if points:
        pts = [s(p) for p in points]
        if len(pts) >= 2:
            d.line(pts, fill="#ffffff", width=w)
        for p in pts:
            crosshair(p, "#ffffff", halo=True)
    return out


# ----------------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------------
with st.sidebar:
    st.header("Settings")
    is_dark = current_theme() == "dark"
    want_dark = st.toggle("🌙 Dark mode", value=is_dark)
    if want_dark != is_dark:
        set_theme("dark" if want_dark else "light")
        st.rerun()
    mode = st.radio("Mode", ["Length (2 points)", "Area (N points)"], index=0)
    units = st.radio("Units", ["ft-in", "mm", "decimal inches"], index=0, horizontal=True)
    view_w = st.slider("Image size (px wide)", 500, 1600, VIEW_W, step=50)
    view_h = round(view_w * VIEW_H / VIEW_W)
    zoom_on = st.toggle("Precise placement (zoom loupe)", value=True,
                        help="First click marks a rough spot; a magnified crop appears "
                             "so you can place the point exactly.")
    zoom_win = st.select_slider("Loupe window (photo px)", options=LOUPE_WINDOWS, value=300,
                                disabled=not zoom_on)
    st.caption(PLANE_WARNING)

    st.divider()
    st.subheader("Capture rules")
    if CAPTURE_RULES.exists():
        st.image(str(CAPTURE_RULES), width="stretch")
    else:
        st.markdown(
            "- ✅ 3–10 ft away, within 45° of straight-on\n"
            "- ✅ Whole board in frame, paper flat, 1× lens\n"
            "- ❌ 0.5× lens, board cut off or at the edge\n"
            "- ❌ Steep angle, curled paper, glare\n"
            "- ❌ Measuring off the board's surface\n\n"
            "*(Cartoon from Pair C appears here once `assets/capture_rules.png` lands.)*"
        )

    tutorial_img = load_asset(str(TUTORIAL), transparent=False)
    if tutorial_img is not None:
        with st.expander("📖 Tutorial: the marker board", expanded=False):
            st.image(tutorial_img, width="stretch")
            st.caption(
                "Four ArUco markers (IDs 0–3) on one flat sheet. Tape it to the surface "
                "you want to measure; the app measures along that surface."
            )

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
hc1, hc2 = st.columns([1, 9], vertical_alignment="center")
with hc1:
    if logo_img is not None:
        st.image(logo_img, width=110)
    else:
        st.markdown("# 📐")
with hc2:
    st.markdown(
        '<div class="app-title">Site Photo Measure</div>'
        f'<div class="app-sub"><b>How it works:</b> {HOW_IT_WORKS}</div>',
        unsafe_allow_html=True,
    )

uploaded = st.file_uploader(
    "Upload a photo (phones: choose *Take Photo*)",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=False,
)

if uploaded is None:
    st.session_state.image_key = None
    st.session_state.bgr = None
    st.session_state.det = None
    st.info("Upload a photo that shows the whole marker board to begin.")
    tutorial_img = load_asset(str(TUTORIAL), transparent=False)
    if tutorial_img is not None:
        tc1, tc2 = st.columns([3, 2], gap="large")
        with tc1:
            st.image(tutorial_img, width="stretch")
        with tc2:
            st.markdown(
                "#### Three steps\n"
                "1. **Tape the marker board** (IDs 0–3) flat on the surface you want to measure.\n"
                "2. **Take a photo** from 3–10 ft, 1× lens, whole board in frame.\n"
                "3. **Upload and click two points** on that surface. Read the length "
                "in ft-in with a ± tolerance.\n\n"
                "Capture rules are in the sidebar."
            )
    st.stop()

# Decode + detect once per upload (not on every click).
image_key = (uploaded.name, uploaded.size)
if st.session_state.image_key != image_key:
    with st.spinner("Detecting markers…"):
        bgr = load_bgr(uploaded)
        det = measure.detect(bgr)
    st.session_state.image_key = image_key
    st.session_state.bgr = bgr
    st.session_state.det = det
    _reset_for_new_image()

bgr: np.ndarray = st.session_state.bgr
det: measure.Detection = st.session_state.det
full_h, full_w = bgr.shape[:2]

# --- Badge ------------------------------------------------------------------
icon = GRADE_ICON.get(det.grade, "⚪")
rms = f"{det.rms_mm:.2f} mm fit" if det.rms_mm is not None else "no fit"
ids = ", ".join(str(i) for i in det.ids) if det.ids else "none"
badge_text = f"{icon} **{det.grade.upper()}** · {rms} · markers {ids} · {det.message}"

if not det.found:
    st.error(
        "**Marker board not found.** Make sure the whole board is in the frame, "
        "flat, well lit, and shot with the 1× lens from 3–10 ft. "
        "See **Capture rules** in the sidebar. " + (det.message or "")
    )
elif det.grade == "green":
    st.success(badge_text)
elif det.grade == "yellow":
    st.warning(badge_text)
else:
    st.error(badge_text)

st.caption(f"⚠️ {PLANE_WARNING}")

# --- Image with overlay + click handling ------------------------------------
overlay_bgr = measure.draw_overlay(bgr, det) if det.found else bgr
overlay_pil = bgr_to_pil(overlay_bgr)

# Fixed viewing box: fit the photo inside view_w x view_h, keeping its aspect.
aspect = full_w / full_h
box_w = round(min(view_w, view_h * aspect))
disp_w = min(2 * box_w, full_w)                 # 2x for high-DPI sharpness
disp_h = max(1, round(full_h * disp_w / full_w))
display = overlay_pil.resize((disp_w, disp_h), Image.LANCZOS)
scale_disp = disp_w / full_w           # full-res -> display

is_area = mode.startswith("Area")
pending = st.session_state.pending if zoom_on else None


def _commit_point(p: tuple[float, float], label: str) -> None:
    """Add a final full-res point; close a length when two are in."""
    pts = st.session_state.points
    if not is_area and len(pts) >= 2:
        pts = []                                  # third click starts a new line
    pts.append(p)
    st.session_state.points = pts
    if not is_area and len(pts) == 2:
        # ~50 ms Monte Carlo over marker-corner noise; called once per line, not per rerun.
        if hasattr(measure, "distance_with_uncertainty"):
            mm, unc, warn = measure.distance_with_uncertainty(det, pts[0], pts[1])
        else:  # older measure.py (pre-A12) or a stale import: length only, no ±
            mm, unc, warn = measure.distance_mm(det.H, pts[0], pts[1]), None, ""
        st.session_state.measurements.append(
            {"label": label, "kind": "length", "mm": mm, "unc": unc, "warn": warn,
             "points": list(pts)}
        )
        st.session_state.points = []
    _clear_pending()


col_img, col_side = st.columns([3, 2], gap="large")

with col_side:
    st.subheader("Measure")
    next_n = len(st.session_state.measurements) + 1
    label = st.text_input("Label for next measurement", value=f"M{next_n}")

    b1, b2 = st.columns(2)
    if b1.button("Clear points", width="stretch"):
        _clear_points()
        st.rerun()
    if b2.button("Undo last", width="stretch", disabled=not st.session_state.measurements):
        st.session_state.measurements.pop()
        st.rerun()
    if is_area:
        if st.button(
            "Close shape",
            type="primary",
            width="stretch",
            disabled=not (det.found and len(st.session_state.points) >= 3),
        ):
            pts = list(st.session_state.points)
            mm2 = measure.area_mm2(det.H, pts)
            st.session_state.measurements.append(
                {"label": label, "kind": "area", "mm2": mm2, "points": pts}
            )
            _clear_points()
            st.rerun()
    n_pts = len(st.session_state.points)
    if is_area:
        st.caption(f"{n_pts} point(s) placed. Click >=3, then **Close shape**.")
    else:
        st.caption(f"{n_pts}/2 points placed. A third click starts a new line.")

    # ---- Zoom loupe: magnified crop around the pending rough click
    loupe_click = None
    loupe_geom = None
    if pending is not None and det.found:
        cw, ch = min(zoom_win, full_w), min(zoom_win, full_h)
        x0 = int(np.clip(round(pending[0] - cw / 2), 0, full_w - cw))
        y0 = int(np.clip(round(pending[1] - ch / 2), 0, full_h - ch))
        crop = overlay_pil.crop((x0, y0, x0 + cw, y0 + ch))
        up = 2 * LOUPE_W / cw                     # 2x for high-DPI
        crop = crop.resize((round(cw * up), round(ch * up)),
                           Image.LANCZOS if up < 1 else Image.BICUBIC)
        crop = draw_annotations(
            crop, up, st.session_state.measurements,
            st.session_state.points + [pending], units, offset=(x0, y0),
            marker_scale=3.0,                     # crop is small; keep crosshair visible
        )
        loupe_geom = (x0, y0, cw, ch)
        st.markdown("**Zoom: click the exact point**")
        with st.container(width=LOUPE_W):     # cap at LOUPE_W, shrink if the column is narrower
            loupe_click = streamlit_image_coordinates(
                crop,
                key=f"loupe_{st.session_state.loupe_nonce}",
                width="stretch",
                image_format="PNG",
                cursor="crosshair",
            )
        px_per_screen = cw / LOUPE_W
        ppm = (det.cal or {}).get("px_per_mm_at_target")
        prec = f" = about {px_per_screen / ppm:.2f} mm" if ppm else ""
        st.caption(f"{cw} px window - {px_per_screen:.2f} photo px per screen px{prec}")
        c1, c2 = st.columns(2)
        if c1.button("Use rough point", width="stretch"):
            _commit_point(pending, label)
            st.rerun()
        if c2.button("Cancel", width="stretch"):
            _clear_pending()
            st.rerun()

with col_img:
    in_progress = st.session_state.points + ([pending] if pending is not None else [])
    annotated = draw_annotations(
        display, scale_disp, st.session_state.measurements, in_progress, units
    )
    if det.found:
        # Container caps the photo at box_w but lets it shrink to fit a narrow
        # column; a fixed component width would overflow and hide part of it.
        with st.container(width=box_w):
            click = streamlit_image_coordinates(
                annotated,
                key=f"click_{st.session_state.click_nonce}",
                width="stretch",
                image_format="JPEG",
                jpeg_quality=92,
                cursor="crosshair",
            )
    else:
        st.image(annotated, width=box_w)
        click = None

# Loupe click -> precise point. (Checked first so it wins over a stale overview value.)
if loupe_click is not None and loupe_click != st.session_state.last_loupe_click:
    st.session_state.last_loupe_click = loupe_click
    x0, y0, cw, ch = loupe_geom
    rw = loupe_click.get("width") or LOUPE_W
    rh = loupe_click.get("height") or round(LOUPE_W * ch / cw)
    x_full = float(np.clip(x0 + loupe_click["x"] * cw / rw, 0, full_w - 1))
    y_full = float(np.clip(y0 + loupe_click["y"] * ch / rh, 0, full_h - 1))
    _commit_point((x_full, y_full), label)
    st.rerun()

# A rerun re-reports the component's last value; only act on a *new* click.
if click is not None and click != st.session_state.last_click:
    st.session_state.last_click = click
    # Component reports {x, y} relative to the *rendered* <img> plus its
    # rendered width/height; normalise to the display copy, then to full-res.
    rw = click.get("width") or disp_w
    rh = click.get("height") or disp_h
    x_full = float(np.clip(click["x"] * disp_w / rw / scale_disp, 0, full_w - 1))
    y_full = float(np.clip(click["y"] * disp_h / rh / scale_disp, 0, full_h - 1))
    if zoom_on:
        st.session_state.pending = (x_full, y_full)   # refine in the loupe
        st.session_state.last_loupe_click = None
        st.session_state.loupe_nonce += 1
    else:
        _commit_point((x_full, y_full), label)
    st.rerun()

# --- Result -----------------------------------------------------------------
with col_side:
    if st.session_state.measurements:
        m = st.session_state.measurements[-1]
        if m["kind"] == "length":
            pm = html.escape(fmt_pm_units(m.get("unc"), units))   # '± <1/16"' has a '<'
            st.markdown(
                f'<div class="big-result">{html.escape(fmt_length(m["mm"], units))}'
                + (f' <span class="pm">{pm}</span>' if pm else "")
                + "</div>",
                unsafe_allow_html=True,
            )
            alts = [u for u in ("ft-in", "mm", "decimal inches") if u != units]
            st.markdown(
                f'<div class="sub-result">{m["label"]} · '
                f'{fmt_length(m["mm"], alts[0])} · {fmt_length(m["mm"], alts[1])}</div>',
                unsafe_allow_html=True,
            )
            if m.get("warn"):
                st.caption(f"⚠️ {m['warn']}")
        else:
            ft2 = m["mm2"] / 92_903.04
            st.markdown(f'<div class="big-result">{ft2:,.2f} ft²</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="sub-result">{m["label"]} · {m["mm2"] / 1e6:,.3f} m² · {m["mm2"] / 645.16:,.1f} in²</div>',
                unsafe_allow_html=True,
            )
    elif det.found:
        st.markdown(
            '<div class="sub-result">Click two points on the photo'
            + (" (or several, for area)" if is_area else "")
            + ".</div>",
            unsafe_allow_html=True,
        )

# --- Measurement list + download ---------------------------------------------
if st.session_state.measurements:
    st.subheader("Measurements")
    rows = []
    for m in st.session_state.measurements:
        if m["kind"] == "length":
            rows.append({"Label": m["label"], "Type": "Length", "Value": fmt_length(m["mm"], units),
                         "±": fmt_pm_units(m.get("unc"), units), "mm": round(m["mm"], 1)})
        else:
            rows.append({"Label": m["label"], "Type": "Area", "Value": fmt_area(m["mm2"]),
                         "±": "", "mm": round(m["mm2"], 0)})
    st.table(rows)

    full_annotated = draw_annotations(
        overlay_pil, 1.0, st.session_state.measurements, [], units
    )
    buf = io.BytesIO()
    full_annotated.convert("RGB").save(buf, format="JPEG", quality=90)
    stem = Path(uploaded.name).stem
    st.download_button(
        "⬇️ Download annotated photo",
        data=buf.getvalue(),
        file_name=f"{stem}_measured.jpg",
        mime="image/jpeg",
    )
