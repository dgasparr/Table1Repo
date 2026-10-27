"""Press-and-hold magnifier click component (GeniusScan style).

Press on the image -> a round magnifier with a crosshair appears in the top corner and
follows the finger/mouse; release -> the point is selected. Everything during the drag
runs in the browser; only the final point goes back to Python.

Returns the same dict as streamlit_image_coordinates, so app.py's mapping code is unchanged:
    {"x", "y", "width", "height", "unix_time"}   # x, y in rendered (CSS) px of the image
"""
import base64
from io import BytesIO
from pathlib import Path

import streamlit.components.v1 as components
from PIL import Image

_component = components.declare_component(
    "magnifier_click", path=str((Path(__file__).parent / "frontend").absolute())
)


def magnifier_click(image: Image.Image, key: str, zoom: float = 3.0, jpeg_quality: int = 90):
    buf = BytesIO()
    image.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
    src = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return _component(src=src, zoom=zoom, key=key, default=None)
