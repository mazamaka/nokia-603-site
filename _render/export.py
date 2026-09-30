"""Export Blender renders to the site: WebP full + small, pure-black backgrounds, frame-ratio padding, OG image."""
from pathlib import Path

import numpy as np
from loguru import logger
from PIL import Image

SRC = Path(__file__).resolve().parent / "out"
DST = Path(__file__).resolve().parent.parent / "assets" / "img"
DST.mkdir(parents=True, exist_ok=True)
PORTS_TOP = 0.0  # fraction of the ports render cropped from the top


def crush(im: Image.Image, floor: int = 3) -> Image.Image:
    """force near-black background noise to exact #000 so images melt into the page"""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    mask = a.max(axis=2) <= floor
    a[mask] = 0
    return Image.fromarray(a.astype(np.uint8))


def pad_to(im: Image.Image, ratio: float, anchor: float = 0.5) -> Image.Image:
    """pad with black to width/height == ratio (anchor: vertical position of the original, 0..1)"""
    w, h = im.size
    target_h = round(w / ratio)
    if target_h <= h:
        return im
    out = Image.new("RGB", (w, target_h), (0, 0, 0))
    out.paste(im, (0, round((target_h - h) * anchor)))
    return out


def portrait_box(names: list[str], margin: float = 0.045, ratio: float = 0.8) -> tuple[int, int, int, int]:
    """one shared 4:5 crop around the phone in all portrait renders, so switching colours never shifts the device"""
    boxes = [crush(Image.open(SRC / f"{n}.png"), 8).getbbox() for n in names]
    x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
    x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
    w, h = Image.open(SRC / f"{names[0]}.png").size
    bh = (y1 - y0) * (1 + 2 * margin)
    bw = max((x1 - x0) * (1 + 2 * margin), bh * ratio)
    bh = bw / ratio
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box = (max(0, round(cx - bw / 2)), max(0, round(cy - bh / 2)), min(w, round(cx + bw / 2)), min(h, round(cy + bh / 2)))
    logger.info("portrait crop {} from {} renders", box, len(names))
    return box


def save(im: Image.Image, name: str, small: int) -> None:
    im.save(DST / f"{name}.webp", "WEBP", quality=84, method=6)
    s = im.resize((small, round(im.height * small / im.width)), Image.LANCZOS)
    s.save(DST / f"{name}-{small}.webp", "WEBP", quality=82, method=6)
    logger.info("{} {}x{} -> {}.webp + -{}.webp ({} KB)", name, im.width, im.height, name, small, (DST / f"{name}.webp").stat().st_size // 1024)


if __name__ == "__main__":
    portraits = [f"hero_{c}" for c in ("black", "white")] + [f"back_{c}" for c in ("black", "white", "fuchsia", "green", "yellow", "blue")]
    box = portrait_box(portraits)
    for n in portraits:
        save(crush(Image.open(SRC / f"{n}.png")).crop(box), n.replace("_", "-"), 800)
    for n in ("duo", "lineup", "profile", "camera", "display", "nfc"):
        save(crush(Image.open(SRC / f"{n}.png")), n, 1200)
    ports = crush(Image.open(SRC / "ports.png"))
    if PORTS_TOP:  # drop the back-cover band above the top edge
        ports = ports.crop((0, round(ports.height * PORTS_TOP), ports.width, ports.height))
    save(pad_to(ports, 16 / 9, 0.42), "ports", 1200)
    save(pad_to(crush(Image.open(SRC / "keys.png")), 2.0, 0.5), "keys", 1200)
    og = Image.open(DST / "duo.webp").convert("RGB").resize((1200, 675), Image.LANCZOS).crop((0, 22, 1200, 652))
    og.save(DST / "og.jpg", quality=88)
    logger.success("export done -> {}", DST)
