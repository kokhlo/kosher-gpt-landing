#!/usr/bin/env python3
"""Draws the site's icons and link previews from the iOS app's own sources.

    python3 tools/images.py

Reads the app icon and the Rubik font from the sibling kosher-gpt-ios repo
(override with --icon and --font) and writes:
  assets/icons/  favicon-32.png, apple-touch-icon.png, icon-96/192/512.png
  assets/og/     <page>-<lang>.png, 1200x630, one per page and language
Needs Pillow. Re-run when the icon or a page heading changes.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IOS = ROOT.parent / "kosher-gpt-ios" / "KosherGPT"
W, H, PAD = 1200, 630, 80
CREAM, FRAME, ACTION, GOLD = (255, 250, 240), (31, 90, 80), (125, 51, 70), (211, 171, 86)


def rubik(path, size, weight):
    font = ImageFont.truetype(str(path), size)
    font.set_variation_by_axes([weight])
    return font


def night_background():
    base = Image.new("RGB", (W, H), (11, 28, 24))
    glow = Image.radial_gradient("L").resize((2000, 1600))
    tint = Image.new("RGB", (W, H), (36, 88, 78))
    mask = Image.new("L", (W, H), 0)
    mask.paste(Image.eval(glow, lambda v: 255 - v), (-200, -500))
    return Image.composite(tint, base, mask)


def wrap(draw, text, font, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    lines.append(line)
    return lines


def draw_arch(draw, x, y, w, h):
    r = w // 2
    draw.rectangle([x, y + r, x + w, y + h], fill=FRAME)
    draw.pieslice([x, y, x + w, y + w], 180, 360, fill=FRAME)
    p = 18
    iw = w - 2 * p
    draw.rectangle([x + p, y + p + iw // 2, x + w - p, y + h], fill=(246, 235, 211))
    draw.pieslice([x + p, y + p, x + w - p, y + p + iw], 180, 360, fill=(246, 235, 211))
    cw, ch, t = int(iw * 0.46), int((h - p) * 0.74), 15
    cx, cy = x + (w - cw) // 2, y + h - ch
    draw.rectangle([cx, cy + cw // 2, cx + cw, y + h], fill=ACTION)
    draw.pieslice([cx, cy, cx + cw, cy + cw], 180, 360, fill=ACTION)
    draw.rectangle([cx + t, cy + cw // 2, cx + cw - t, y + h], fill=(246, 235, 211))
    draw.pieslice([cx + t, cy + t, cx + cw - t, cy + cw - t], 180, 360, fill=(246, 235, 211))
    draw.rounded_rectangle([x - 30, y + h, x + w + 30, y + h + 22], radius=11, fill=FRAME)


def og_card(title, rtl, icon, font_path, out):
    img = night_background()
    d = ImageDraw.Draw(img)
    draw_arch(d, 860, 150, 250, 330)
    brand_font = rubik(font_path, 34, 600)
    img.paste(icon.resize((60, 60)), (PAD, PAD))
    d.text((PAD + 78, PAD + 30), "KosherGPT", font=brand_font, fill=CREAM, anchor="lm")
    title_font = rubik(font_path, 66, 600)
    box = 700
    y = 230
    for line in wrap(d, title, title_font, box):
        shown = line[::-1] if rtl else line  # Pillow without libraqm lays text left to right
        x = PAD + box - d.textlength(shown, font=title_font) if rtl else PAD
        d.text((x, y), shown, font=title_font, fill=CREAM)
        y += 80
    d.text((PAD, H - PAD), "kosherno.app", font=rubik(font_path, 28, 400), fill=(200, 210, 200), anchor="ls")
    d.rectangle([PAD, H - PAD + 14, PAD + 60, H - PAD + 18], fill=GOLD)
    img.save(out, "PNG", optimize=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--icon", default=str(IOS / "Design" / "AppIconSource.png"))
    parser.add_argument("--font", default=str(IOS / "Resources" / "Rubik-Variable.ttf"))
    args = parser.parse_args()
    icon = Image.open(args.icon).convert("RGB")

    icons = ROOT / "assets" / "icons"
    icons.mkdir(parents=True, exist_ok=True)
    for name, size in [("favicon-32.png", 32), ("apple-touch-icon.png", 180), ("icon-96.png", 96),
                       ("icon-192.png", 192), ("icon-512.png", 512)]:
        icon.resize((size, size), Image.LANCZOS).save(icons / name, optimize=True)
        print("wrote", f"assets/icons/{name}")

    og = ROOT / "assets" / "og"
    og.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "ru", "he"):
        c = json.loads((ROOT / "content" / f"{lang}.json").read_text(encoding="utf-8"))
        for page in ("home", "partners"):
            og_card(c[page]["og_title"], c["dir"] == "rtl", icon, args.font, og / f"{page}-{lang}.png")
            print("wrote", f"assets/og/{page}-{lang}.png")


if __name__ == "__main__":
    main()
