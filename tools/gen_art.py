"""Builds derived artwork from assets/alfred.png (the official logo).

    python tools/gen_art.py

Outputs
  assets/alfred.ico                 16–256 px (small sizes use the head close-up for legibility)
  assets/alfred_tray.png            256 px tray / small UI icon (head close-up inside the gold ring)
  assets/installer/wizard_*.bmp     Inno Setup side images (100%–250% DPI)
  assets/installer/small_*.bmp      Inno Setup header images (100%–250% DPI)
  docs/banner.png                   1280×640 repository / social preview image
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
LOGO = Image.open(ASSETS / "alfred.png").convert("RGBA")
FONTS = ASSETS / "fonts"

BLACK = (8, 9, 13)
GRAPHITE = (21, 23, 30)
GOLD = (212, 175, 55)
GOLD_LIGHT = (255, 216, 77)
WHITE = (245, 245, 245)


def head_icon(size: int) -> Image.Image:
    """Close-up of the butler's face inside a gold ring (legible at 16–32 px)."""
    cx, cy, r = 510, 330, 250
    big = 512
    crop = LOGO.crop((cx - r, cy - r, cx + r, cy + r)).resize((big, big), Image.Resampling.LANCZOS)
    disc = Image.new("RGBA", (big, big), (*GRAPHITE, 255))
    disc.alpha_composite(crop)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((18, 18, big - 18, big - 18), fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(disc, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((12, 12, big - 12, big - 12), outline=(*GOLD, 255), width=30)
    small = out.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 32:
        small = small.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
    return small


def full_icon(size: int) -> Image.Image:
    im = LOGO.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 64:
        im = im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=50, threshold=1))
    return im


def build_ico() -> None:
    sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    frames = [head_icon(s) if s <= 32 else full_icon(s) for s in sizes]
    frames[-1].save(ASSETS / "alfred.ico", format="ICO", sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    head_icon(256).save(ASSETS / "alfred_tray.png")


def gradient(w: int, h: int) -> Image.Image:
    base = Image.new("RGB", (w, h), BLACK)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(glow)
    r = int(max(w, h) * 0.55)
    d.ellipse((w * 0.5 - r, h * 0.28 - r, w * 0.5 + r, h * 0.28 + r), fill=(*GOLD, 40))
    glow = glow.filter(ImageFilter.GaussianBlur(max(w, h) * 0.12))
    base = Image.alpha_composite(base.convert("RGBA"), glow)
    shade = Image.linear_gradient("L").resize((w, h))
    dark = Image.new("RGBA", (w, h), (*GRAPHITE, 255))
    dark.putalpha(shade.point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(base, dark)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


def build_installer_images() -> None:
    out = ASSETS / "installer"
    out.mkdir(exist_ok=True)
    for pct in (100, 125, 150, 175, 200, 250):
        k = pct / 100
        w, h = round(164 * k), round(314 * k)
        img = gradient(w, h)
        logo_size = round(132 * k)
        img.alpha_composite(full_icon(logo_size), ((w - logo_size) // 2, round(40 * k)))
        d = ImageDraw.Draw(img)
        f = font("Inter-SemiBold.otf", round(17 * k))
        text = "A L F R E D"
        tw = d.textlength(text, font=f)
        d.text(((w - tw) / 2, round(196 * k)), text, font=f, fill=(*GOLD_LIGHT, 255))
        d.line((w * 0.3, round(226 * k), w * 0.7, round(226 * k)), fill=(*GOLD, 160), width=max(1, round(k)))
        f2 = font("Lora-Italic-Variable.ttf", round(11 * k))
        for i, line in enumerate(("Algumas tarefas é melhor", "deixar para o Alfred.")):
            lw = d.textlength(line, font=f2)
            d.text(((w - lw) / 2, round((238 + i * 15) * k)), line, font=f2, fill=(*WHITE, 210))
        img.convert("RGB").save(out / f"wizard_{pct}.bmp")
        s = round(55 * k)
        small = Image.new("RGBA", (s, s), (255, 255, 255, 255))
        small.alpha_composite(head_icon(s))
        small.convert("RGB").save(out / f"small_{pct}.bmp")


def build_banner() -> None:
    w, h = 1280, 640
    img = gradient(w, h)
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((90, 90, 550, 550), fill=(*GOLD, 70))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(60)))
    img.alpha_composite(full_icon(440), (100, 100))
    d = ImageDraw.Draw(img)
    d.text((620, 190), "ALFRED", font=font("InterDisplay-SemiBold.otf", 120), fill=(*WHITE, 255))
    d.text((626, 330), "Conversor universal de arquivos para Windows", font=font("Inter-Medium.otf", 26),
           fill=(*GOLD_LIGHT, 255))
    d.line((626, 390, 1150, 390), fill=(*GOLD, 150), width=2)
    d.text((626, 410), "“Algumas tarefas é melhor deixar para o Alfred.”",
           font=font("Lora-Italic-Variable.ttf", 27), fill=(*WHITE, 225))
    d.text((626, 480), "Selecionou. Arrastou. Escolheu. Converteu.", font=font("Inter-Regular.otf", 24),
           fill=(200, 200, 205, 255))
    (ROOT / "docs").mkdir(exist_ok=True)
    img.convert("RGB").save(ROOT / "docs" / "banner.png", optimize=True)


if __name__ == "__main__":
    build_ico()
    build_installer_images()
    build_banner()
    print("arte gerada")
