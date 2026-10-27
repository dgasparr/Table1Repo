// Press-and-hold magnifier. Press: show loupe; move: update it; release: send the point.
const img = document.getElementById("image");
const loupe = document.getElementById("loupe");
const ctx = loupe.getContext("2d");
let zoom = 3;
let active = false;

function fitFrame() {
  Streamlit.setFrameHeight(Math.ceil(img.getBoundingClientRect().height));
}

function pos(e) {
  const r = img.getBoundingClientRect();
  return {
    x: Math.min(Math.max(e.clientX - r.left, 0), r.width - 0.01),
    y: Math.min(Math.max(e.clientY - r.top, 0), r.height - 0.01),
    w: r.width,
    h: r.height,
  };
}

function drawLoupe(p) {
  const L = Math.round(Math.min(180, Math.max(110, p.w * 0.38)));
  const dpr = window.devicePixelRatio || 1;
  const S = Math.round(L * dpr);
  if (loupe.width !== S) {
    loupe.width = S; loupe.height = S;
    loupe.style.width = L + "px"; loupe.style.height = L + "px";
  }
  // Top-right by default; jump to top-left when the finger is under that corner.
  const nearTopRight = p.x > p.w - L - 24 && p.y < L + 24;
  loupe.style.left = nearTopRight ? "8px" : "";
  loupe.style.right = nearTopRight ? "" : "8px";

  const k = img.naturalWidth / p.w;          // natural px per CSS px
  const src = (L / zoom) * k;                // source square, natural px
  ctx.save();
  ctx.clearRect(0, 0, S, S);
  ctx.beginPath();
  ctx.arc(S / 2, S / 2, S / 2, 0, 2 * Math.PI);
  ctx.clip();
  ctx.fillStyle = "#111";
  ctx.fillRect(0, 0, S, S);
  ctx.imageSmoothingEnabled = true;
  // Clip the source square to the image (some browsers draw nothing if it pokes outside).
  const sx = p.x * k - src / 2, sy = p.y * k - src / 2;
  const cx0 = Math.max(sx, 0), cy0 = Math.max(sy, 0);
  const cx1 = Math.min(sx + src, img.naturalWidth), cy1 = Math.min(sy + src, img.naturalHeight);
  if (cx1 > cx0 && cy1 > cy0) {
    const f = S / src;
    ctx.drawImage(img, cx0, cy0, cx1 - cx0, cy1 - cy0,
                  (cx0 - sx) * f, (cy0 - sy) * f, (cx1 - cx0) * f, (cy1 - cy0) * f);
  }

  // Crosshair with a gap in the middle so the exact pixel stays visible.
  const c = S / 2, g = 6 * dpr, a = S * 0.42;
  const seg = [[c - a, c, c - g, c], [c + g, c, c + a, c], [c, c - a, c, c - g], [c, c + g, c, c + a]];
  for (const [w, col] of [[4 * dpr, "rgba(0,0,0,.75)"], [2 * dpr, "#00e5ff"]]) {
    ctx.lineWidth = w; ctx.strokeStyle = col;
    ctx.beginPath();
    for (const [x1, y1, x2, y2] of seg) { ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); }
    ctx.stroke();
  }
  ctx.fillStyle = "#ff2d55";
  ctx.beginPath(); ctx.arc(c, c, 1.5 * dpr, 0, 2 * Math.PI); ctx.fill();
  ctx.restore();
}

img.addEventListener("pointerdown", (e) => {
  if (e.button !== undefined && e.button > 0) return;   // left mouse / touch / pen only
  e.preventDefault();
  img.setPointerCapture(e.pointerId);
  active = true;
  loupe.style.display = "block";
  drawLoupe(pos(e));
});

img.addEventListener("pointermove", (e) => {
  if (!active) return;
  e.preventDefault();
  drawLoupe(pos(e));
});

img.addEventListener("pointerup", (e) => {
  if (!active) return;
  active = false;
  loupe.style.display = "none";
  const p = pos(e);
  Streamlit.setComponentValue({ x: p.x, y: p.y, width: p.w, height: p.h, unix_time: Date.now() });
});

img.addEventListener("pointercancel", () => { active = false; loupe.style.display = "none"; });
img.addEventListener("contextmenu", (e) => e.preventDefault());

function onRender(event) {
  const args = event.detail.args;
  zoom = args.zoom || 3;
  if (img.src !== args.src) {
    img.onload = fitFrame;
    img.src = args.src;
  } else {
    fitFrame();
  }
}

new ResizeObserver(fitFrame).observe(img);
Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
