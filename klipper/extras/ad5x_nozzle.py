# The nozzle size: SET_NOZZLE_SIZE writes it to the printer's own
# nozzle.cfg (config folder, never touched by updates), which ad5x.cfg
# includes after the factory [extruder] (0.4 mm) and before unit.cfg and
# local.cfg; then Klipper restarts. Used by the setup wizard's Nozzle Size
# step and HelixScreen's Settings (patch 0008).
#
# SET_NOZZLE_SIZE SIZE=0.2|0.25|0.4|0.6|0.8|1.0 [RESTART=0]
# printer.ad5x_nozzle: size (the nozzle_diameter Klipper runs with), saved
#   (nozzle.cfg's, null without one), sizes (offered), local (local.cfg
#   sets nozzle_diameter, which then wins over nozzle.cfg).
# Everything sized from the nozzle follows nozzle_diameter: the prime line
# width, the IFS purge lengths (nozzle / 0.4), the setup wizard's Z test,
# Klipper's max_extrude_cross_section.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import os
import re

CONFIG_DIR = "/home/klipper/printer_data/config"
SIZES = (0.2, 0.25, 0.4, 0.6, 0.8, 1.0)
HEADER = """\
# This printer's nozzle size (docs/print-start.md). Written by
# SET_NOZZLE_SIZE (the setup wizard's Nozzle Size step, Settings on the
# touch screen); updates never change it. local.cfg can still override it.
"""
LINE_RE = re.compile(r"^\s*nozzle_diameter\s*[:=]\s*([0-9.]+)", re.M)
SECTION_RE = re.compile(r"^\s*\[extruder\]\s*$", re.M)


def read_size(path):
    """nozzle_diameter set in an [extruder] section of path, else None."""
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        return None
    sect = SECTION_RE.search(text)
    if sect is None:
        return None
    rest = text[sect.end():]
    nxt = re.search(r"^\s*\[", rest, re.M)
    body = rest[:nxt.start()] if nxt else rest
    m = LINE_RE.search(body)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def nozzle_text(size):
    return HEADER + "[extruder]\nnozzle_diameter: %g\n" % (size,)


class AD5XNozzle:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        cdir = config.get('config_dir', CONFIG_DIR)
        self.file = os.path.join(cdir, 'nozzle.cfg')
        self.local = os.path.join(cdir, 'local.cfg')
        # Read at start and after SET_NOZZLE_SIZE, not in get_status (called
        # several times a second for subscribers)
        self.saved = read_size(self.file)
        self.local_size = read_size(self.local)
        self.gcode.register_command(
            "SET_NOZZLE_SIZE", self.cmd_SET_NOZZLE_SIZE,
            desc="This printer's nozzle size: SIZE= (mm), Klipper restarts")

    def _running_size(self):
        cf = self.printer.lookup_object('configfile', None)
        if cf is None:
            return None
        try:
            settings = cf.get_status(None)['settings']
            return float(settings['extruder']['nozzle_diameter'])
        except (KeyError, TypeError, ValueError):
            return None

    def cmd_SET_NOZZLE_SIZE(self, gcmd):
        size = gcmd.get_float('SIZE')
        match = [s for s in SIZES if abs(s - size) < .001]
        if not match:
            raise gcmd.error("SIZE is one of %s (mm)" % (
                ", ".join("%g" % s for s in SIZES),))
        size = match[0]
        ps = self.printer.lookup_object('print_stats', None)
        if ps is not None and ps.get_status(None).get('state') in (
                'printing', 'paused'):
            raise gcmd.error("The nozzle size can't change during a print")
        try:
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                f.write(nozzle_text(size))
            os.replace(tmp, self.file)
        except OSError as e:
            raise gcmd.error("Can't write %s: %s" % (self.file, e))
        self.saved = size
        local = self.local_size = read_size(self.local)
        msg = "Nozzle size %g mm saved (nozzle.cfg)" % (size,)
        if local is not None and abs(local - size) > .001:
            msg += ("; local.cfg sets nozzle_diameter: %g, which wins: "
                    "remove it there" % (local,))
        gcmd.respond_info(msg)
        logging.info("ad5x_nozzle: %s", msg)
        if gcmd.get_int('RESTART', 1):
            self.gcode.run_script_from_command("RESTART")

    def get_status(self, eventtime):
        return {'size': self._running_size(),
                'saved': self.saved,
                'local': self.local_size is not None,
                'sizes': list(SIZES)}


def load_config(config):
    return AD5XNozzle(config)
