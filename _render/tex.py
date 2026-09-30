"""Textures for the Nokia 603 Blender model (24 px/mm, phone-centred mm coordinates, y up).

Front: base colour (black / white housing) + emission (screen content).
Back: grayscale masks (speaker holes, 'Nokia 603' print, NOKIA badge), mirrored for back-facing planar UVs.
Screen content 'home' is the real Symbian Belle home screen, rectified from the LPC wiki photo.
"""
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

REF = Path(__file__).resolve().parent / "ref"
OUT = Path(__file__).resolve().parent / "tex"
OUT.mkdir(exist_ok=True)

PPM = 24
W_MM, H_MM = 57.1, 113.5
TW, TH = round(W_MM * PPM), round(H_MM * PPM)
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"

# screen active area (3.5" 16:9), mm
SCR = dict(x0=-21.8, x1=21.8, y0=37.75, y1=-39.75)


def px(x: float) -> float:
    return (x + W_MM / 2) * PPM


def py(y: float) -> float:
    return (H_MM / 2 - y) * PPM


def box(cx: float, cy: float, w: float, h: float) -> list[float]:
    return [px(cx - w / 2), py(cy + h / 2), px(cx + w / 2), py(cy - h / 2)]


def font_face(style: str, size: int) -> ImageFont.FreeTypeFont:
    for i in range(20):
        try:
            f = ImageFont.truetype(AVENIR, size, index=i)
        except OSError:
            break
        if f.getname()[1] == style:
            return f
    raise ValueError(style)


def text_mask(text: str, style: str, cap_mm: float, stretch: float = 1.0, width_mm: float | None = None) -> Image.Image:
    f = font_face(style, 400)
    t = Image.new("L", (2600, 700), 0)
    ImageDraw.Draw(t).text((40, 40), text, font=f, fill=255)
    t = t.crop(t.getbbox())
    h = round(cap_mm * PPM)
    w = round(width_mm * PPM) if width_mm else round(t.width * h / t.height * stretch)
    return t.resize((w, h), Image.LANCZOS)


def paste_center(dst: Image.Image, mask: Image.Image, cx: float, cy: float, color) -> None:
    x, y = round(px(cx) - mask.width / 2), round(py(cy) - mask.height / 2)
    dst.paste(color, (x, y, x + mask.width, y + mask.height), mask)


def handset(d: ImageDraw.ImageDraw, cx: float, cy: float, color, w_mm: float = 2.3, flip: bool = False) -> None:
    w, h = w_mm * PPM, w_mm * PPM * 0.9
    x, y = px(cx), py(cy)
    bb = [x - w / 2, y - h * 0.15, x + w / 2, y + h * 0.85] if not flip else [x - w / 2, y - h * 0.55, x + w / 2, y + h * 0.45]
    lw = max(3, round(0.28 * PPM))
    d.arc(bb, 200, 340, fill=color, width=lw)
    r = 0.26 * PPM
    for ang_pt in ((bb[0] + w * 0.06, y + h * 0.22), (bb[2] - w * 0.06, y + h * 0.22)):
        d.ellipse([ang_pt[0] - r, ang_pt[1] - r * 0.8, ang_pt[0] + r, ang_pt[1] + r * 0.8], fill=color)


def front(kind: str) -> Image.Image:
    dark = kind == "black"
    c = dict(
        bg=(7, 7, 8) if dark else (238, 238, 236),
        win=(2, 2, 3) if dark else (5, 5, 6),
        ear=(24, 25, 28) if dark else (201, 202, 205),
        mesh=(12, 13, 15) if dark else (176, 178, 182),
        sensor=(17, 18, 20) if dark else (207, 208, 211),
        logo=(184, 187, 192) if dark else (112, 116, 122),
        strip=(17, 18, 21) if dark else (223, 224, 227),
        strip_hi=(43, 45, 51) if dark else (247, 247, 248),
        menu=(174, 178, 184) if dark else (139, 143, 149),
        mic=(15, 16, 18) if dark else (196, 198, 201),
    )
    im = Image.new("RGB", (TW, TH), c["bg"])
    d = ImageDraw.Draw(im)
    # display window (white housing shows a black border around the panel)
    m = 0.0 if dark else 0.9
    d.rectangle([px(SCR["x0"] - m), py(SCR["y0"] + m), px(SCR["x1"] + m), py(SCR["y1"] - m)], fill=c["win"])
    # earpiece slot with mesh
    eb = box(0, 49.1, 10.4, 1.25)
    d.rounded_rectangle(eb, radius=0.62 * PPM, fill=c["ear"])
    step = round(0.3 * PPM)
    for yy in range(round(eb[1]) + 4, round(eb[3]) - 3, step):
        for xx in range(round(eb[0]) + 10, round(eb[2]) - 9, step):
            d.ellipse([xx - 2, yy - 2, xx + 2, yy + 2], fill=c["mesh"])
    # proximity / light sensor
    sb = box(-14.35, 47.85, 1.5, 1.5)
    d.ellipse(sb, fill=c["sensor"], outline=c["strip_hi"], width=2)
    # wordmark
    paste_center(im, text_mask("NOKIA", "Demi Bold", 1.9, width_mm=12.2), 0, 43.1, c["logo"])
    # key strip: call / menu / end
    kb = box(0, -45.3, 41, 2.8)
    d.rounded_rectangle(kb, radius=1.4 * PPM, fill=c["strip"])
    d.line([kb[0] + 1.4 * PPM, kb[1] + 2, kb[2] - 1.4 * PPM, kb[1] + 2], fill=c["strip_hi"], width=2)
    handset(d, -16.5, -45.45, (57, 181, 74))
    d.rounded_rectangle(box(0, -45.3, 3.2, 0.42), radius=0.2 * PPM, fill=c["menu"])
    handset(d, 16.5, -45.15, (224, 57, 62), flip=True)
    # microphone
    d.rounded_rectangle(box(0, -53.6, 2.4, 0.5), radius=0.25 * PPM, fill=c["mic"])
    return im


def screen_from_photo() -> Image.Image:
    src = Image.open(REF / "lpc_603front.jpg").convert("RGB")
    # quad: UL, LL, LR, UR (measured edges of the lit panel in the photo)
    quad = (293.5, 614, 297.8, 2408, 1312, 2408, 1299.5, 614)
    w, h = round((SCR["x1"] - SCR["x0"]) * PPM), round((SCR["y0"] - SCR["y1"]) * PPM)
    im = src.transform((w, h), Image.QUAD, quad, resample=Image.BICUBIC)
    im = im.filter(ImageFilter.GaussianBlur(0.7)).filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    im = ImageEnhance.Contrast(im).enhance(1.10)
    im = ImageEnhance.Color(im).enhance(1.12)
    return im


def screen_from_png(name: str) -> Image.Image:
    im = Image.open(REF / name).convert("RGB")
    w, h = round((SCR["x1"] - SCR["x0"]) * PPM), round((SCR["y0"] - SCR["y1"]) * PPM)
    return im.resize((w, h), Image.LANCZOS)


def emit(screen: Image.Image | None) -> Image.Image:
    im = Image.new("RGB", (TW, TH), (0, 0, 0))
    if screen is not None:
        im.paste(screen, (round(px(SCR["x0"])), round(py(SCR["y0"]))))
    return im


def back_masks() -> dict[str, Image.Image]:
    holes = Image.new("L", (TW, TH), 0)
    d = ImageDraw.Draw(holes)
    rows, cols, pxm, pym, dia = 6, 38, 1.016, 1.05, 0.55
    for r in range(rows):
        for k in range(cols):
            cx = (k - (cols - 1) / 2) * pxm
            cy = -43.3 + ((rows - 1) / 2 - r) * pym
            d.ellipse(box(cx, cy, dia, dia), fill=255)
    text = Image.new("L", (TW, TH), 0)
    paste_center(text, text_mask("Nokia 603", "Medium", 1.45), 0, -49.9, 255)
    badge = Image.new("L", (TW, TH), 0)
    b = text_mask("NOKIA", "Bold", 3.9, width_mm=16.4).rotate(90, expand=True)  # reads bottom -> top
    paste_center(badge, b, 0, 1.2, 255)
    # drawn as seen from behind -> mirror for planar UVs in object space
    return {k: ImageOps.mirror(v) for k, v in dict(holes=holes, text=text, badge=badge).items()}


if __name__ == "__main__":
    for kind in ("black", "white"):
        front(kind).save(OUT / f"front_{kind}.png")
    home = screen_from_photo()
    home.save(OUT / "screen_home.png")
    emit(home).save(OUT / "emit_home.png")
    emit(screen_from_png("commons_screen.png")).save(OUT / "emit_dolby.png")
    emit(None).save(OUT / "emit_off.png")
    for k, v in back_masks().items():
        v.save(OUT / f"back_{k}.png")
    logger.info("textures -> {} ({}x{} px, {} px/mm)", OUT, TW, TH, PPM)
