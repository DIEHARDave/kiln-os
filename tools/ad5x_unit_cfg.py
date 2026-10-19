#!/usr/bin/env python3
"""Write unit.cfg (per-printer calibration) from the stock settings file.

usage: ad5x_unit_cfg.py [SETTINGS_JSON] [-o unit.cfg]

The stock app keeps each printer's calibration in
/usr/prog/config/Adventurer5M.json. With no file (or a missing one) the
stock defaults are written. Runs on the laptop and on the printer
(installed as /usr/bin/ad5x-unit-cfg; S05ad5x-data runs it at first boot).
"""
import argparse
import json
import sys

# (variable, settings section, key, meaning)
FIELDS = [
    ("z_offset", "leftExtruderOffset", "zProbeOffset",
     "Z offset tuned on the screen; applied at print start"),
    ("cut_x_offset", "leftExtruderOffset", "CutXOffset",
     "cutter position, X (cut at X -2.5 + this)"),
    ("cut_y_offset", "leftExtruderOffset", "CutYOffset",
     "cutter position, Y (cut at Y -7.5 + this)"),
    ("x_offset", "leftExtruderOffset", "xOffset",
     "purge box position, X"),
    ("y_offset", "leftExtruderOffset", "yOffset",
     "purge box position, Y"),
]


def read_settings(path):
    if not path:
        return {}, "stock defaults (no settings file)"
    try:
        with open(path) as f:
            return json.load(f), path
    except (OSError, ValueError) as e:
        print("ad5x_unit_cfg: %s: %s; using stock defaults" % (path, e),
              file=sys.stderr)
        return {}, "stock defaults (%s unreadable)" % path


def render(settings, source):
    out = [
        "# Per-printer calibration, from the stock settings file.",
        "# Source: %s" % source,
        "# Written by ad5x-unit-cfg; edit by hand if needed (it is only",
        "# generated when this file doesn't exist).",
        "[gcode_macro _AD5X_UNIT]",
        "description: Per-printer calibration values (read by other macros)",
    ]
    for var, section, key, meaning in FIELDS:
        value = settings.get(section, {}).get(key, 0.0)
        try:
            value = float(value)
        except (TypeError, ValueError):
            value = 0.0
        out.append("# %s.%s: %s" % (section, key, meaning))
        out.append("variable_%s: %s" % (var, round(value, 4)))
    out += ["gcode:", "  RESPOND MSG=\"unit: %s\"" % ", ".join(
        "%s={%s}" % (v, v)
        for v, _, _, _ in FIELDS), ""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("settings", nargs="?")
    ap.add_argument("-o", "--output", default="-")
    args = ap.parse_args()
    text = render(*read_settings(args.settings))
    if args.output == "-":
        sys.stdout.write(text)
    else:
        with open(args.output, "w") as f:
            f.write(text)


if __name__ == "__main__":
    main()
