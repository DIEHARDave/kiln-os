#!/usr/bin/env python3
"""Boot logo for Kiln OS: 800x480 baseline JPEG (the panel size).

usage: make_logo.py [--recovery] [-o logo.jpg]
Noto Sans (SIL OFL), as HelixScreen uses. Shown at boot by
S07ad5x-board until HelixScreen takes the screen. --recovery: the recovery
OS's logo (board/ad5x-recovery/rootfs-overlay/usr/share/ad5x/recovery-logo.jpg).
"""
import os
import argparse
from PIL import Image, ImageDraw, ImageFont

W, H = 800, 480
# Noto Sans: Arch's path, then Debian's (fonts-noto-core, the builder)
FONTS = next((d for d in ("/usr/share/fonts/noto", "/usr/share/fonts/truetype/noto")
              if os.path.isfile(d + "/NotoSans-Regular.ttf")), "/usr/share/fonts/noto")
BG_TOP, BG_BOTTOM = (16, 20, 27), (28, 36, 48)
WHITE, ACCENT, MUTED = (240, 243, 247), (74, 144, 226), (120, 132, 150)
RECOVERY_ACCENT = (232, 146, 52)


def font(name, size):
    return ImageFont.truetype("%s/NotoSans-%s.ttf" % (FONTS, name), size)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-o", "--output", default="logo.jpg")
    ap.add_argument("--recovery", action="store_true",
                    help="recovery OS variant")
    args = ap.parse_args()
    out = args.output
    accent = RECOVERY_ACCENT if args.recovery else ACCENT
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):               # vertical gradient
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(
            round(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))
    big, small, foot = font("Black", 150), font("Light", 62), font("Regular", 20)
    title, sub = "Kiln", "recovery" if args.recovery else "OS"
    tb = d.textbbox((0, 0), title, font=big)
    sb = d.textbbox((0, 0), sub, font=small)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    sw, sh = sb[2] - sb[0], sb[3] - sb[1]
    gap, bar = 26, 6
    top = (H - (th + gap + bar + gap + sh)) // 2 - 10
    d.text(((W - tw) // 2 - tb[0], top - tb[1]), title, font=big, fill=WHITE)
    y = top + th + gap
    d.rounded_rectangle([(W - 120) // 2, y, (W + 120) // 2, y + bar],
                        radius=3, fill=accent)
    y += bar + gap
    d.text(((W - sw) // 2 - sb[0], y - sb[1]), sub, font=small, fill=accent)
    note = ("update  ·  backup  ·  rescue" if args.recovery
            else "Klipper  ·  open source  ·  for the Flashforge AD5X")
    nb = d.textbbox((0, 0), note, font=foot)
    d.text(((W - (nb[2] - nb[0])) // 2, H - 48), note, font=foot, fill=MUTED)
    img.save(out, "JPEG", quality=92, optimize=True, progressive=False,
             subsampling=0)
    print("wrote", out)


if __name__ == "__main__":
    main()
