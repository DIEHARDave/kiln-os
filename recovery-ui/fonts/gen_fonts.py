#!/usr/bin/env python3
"""Regenerate the embedded Noto Sans subsets (fonts/*.c) for ad5x-recovery-ui.

usage: gen_fonts.py [NOTO_DIR]   (default /usr/share/fonts/noto)

Noto Sans / Noto Sans Mono (SIL OFL 1.1, fonts/OFL-1.1.txt), cut down to
Latin-1 plus a few punctuation marks and stripped of hinting, then written
as C arrays. LVGL's Tiny TTF renders them at run time at any size; icons
(LV_SYMBOL_*) come from LVGL's built-in Montserrat as the fallback font.
The output is committed, so the build needs neither fontTools nor the fonts.
"""
import io
import os
import sys

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = {
    "noto_sans_regular": "NotoSans-Regular.ttf",
    "noto_sans_bold": "NotoSans-Bold.ttf",
    "noto_sans_mono": "NotoSansMono-Regular.ttf",
}
UNICODES = (list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) +
            [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026])


def cut(path):
    opts = subset.Options()
    opts.hinting = False
    opts.desubroutinize = True
    opts.layout_features = ["kern"]
    opts.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]   # keep copyright/licence
    opts.notdef_outline = True
    font = TTFont(path)
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=UNICODES)
    sub.subset(font)
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/noto"
    for name, fname in FONTS.items():
        data = cut(os.path.join(src, fname))
        lines = ["/* %s, subset by gen_fonts.py. SIL Open Font License 1.1"
                 " (OFL-1.1.txt). */" % fname,
                 "#include <stddef.h>",
                 "#include <stdint.h>",
                 "const uint8_t %s_ttf[] = {" % name]
        for i in range(0, len(data), 16):
            lines.append("  " + ",".join("0x%02x" % b for b in data[i:i + 16]) + ",")
        lines.append("};")
        lines.append("const size_t %s_ttf_len = %d;" % (name, len(data)))
        with open(os.path.join(HERE, name + ".c"), "w") as f:
            f.write("\n".join(lines) + "\n")
        print("%s: %d bytes" % (name, len(data)))


if __name__ == "__main__":
    main()
