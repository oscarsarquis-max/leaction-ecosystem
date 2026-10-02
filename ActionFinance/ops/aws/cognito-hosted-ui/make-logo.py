"""Crop the official blue wordmark to the classic Hosted UI logo slot."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "frontend" / "src" / "assets" / "brand" / "actionfinance-blue.png"
DST = Path(__file__).resolve().parent / "logo-hosted-ui.png"
MARK = (22, 3, 173)
MAX_W, MAX_H = 350, 178

im = Image.open(SRC).convert("RGB")
ratio = min(MAX_W / im.width, MAX_H / im.height)
size = (max(1, int(im.width * ratio)), max(1, int(im.height * ratio)))
fitted = im.resize(size, Image.Resampling.LANCZOS)
canvas = Image.new("RGB", (MAX_W, MAX_H), MARK)
canvas.paste(fitted, ((MAX_W - size[0]) // 2, (MAX_H - size[1]) // 2))
canvas.save(DST, format="PNG", optimize=True)
print(f"{DST.name} {canvas.size} {DST.stat().st_size} bytes")
if DST.stat().st_size > 100 * 1024:
    raise SystemExit("logo exceeds the classic Hosted UI 100 KB limit")
