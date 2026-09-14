"""
Trim only peripheral transparency from the official SegSense logo.

Does not rewrite `frontend/images/segsense logo.png`.
Approved by SEGSENSE_PRM_018 for display crop only: same drawing, colours
and proportion; no redesign, distortion, or crop of symbol/name/tagline.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = ROOT / "frontend" / "images" / "segsense logo.png"
DERIVED = ROOT / "frontend" / "images" / "segsense-logo-header.png"
EXPECTED_OFFICIAL = "CEF4A9C0B8F7B0D8F2A50D85DE41FEA02498B15E3021EBB063E75945810C089D"
ALPHA_THRESHOLD = 8
PAD_PX = 24


def main() -> None:
    official_bytes = OFFICIAL.read_bytes()
    official_sha = sha256(official_bytes).hexdigest().upper()
    if official_sha != EXPECTED_OFFICIAL:
        raise SystemExit(f"official SHA mismatch: {official_sha}")
    image = Image.open(OFFICIAL).convert("RGBA")
    bbox = image.getchannel("A").point(lambda p: 255 if p > ALPHA_THRESHOLD else 0).getbbox()
    if bbox is None:
        raise SystemExit("official logo has no visible pixels")
    crop = (
        max(0, bbox[0] - PAD_PX),
        max(0, bbox[1] - PAD_PX),
        min(image.size[0], bbox[2] + PAD_PX),
        min(image.size[1], bbox[3] + PAD_PX),
    )
    derived = image.crop(crop)
    DERIVED.parent.mkdir(parents=True, exist_ok=True)
    derived.save(DERIVED, "PNG", optimize=True)
    after_official = sha256(OFFICIAL.read_bytes()).hexdigest().upper()
    if after_official != EXPECTED_OFFICIAL:
        raise SystemExit("official file changed during trim; abort")
    print(f"bbox={bbox}")
    print(f"crop={crop} size={derived.size}")
    print(f"official_sha={official_sha}")
    print(f"derived={DERIVED} bytes={DERIVED.stat().st_size}")


if __name__ == "__main__":
    main()
