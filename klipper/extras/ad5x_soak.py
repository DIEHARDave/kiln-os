# Bed heat soak: how long the bed needs after reaching its temperature
# before Z is measured, from a calibration with the load-cell probe
#
# The plate's surface keeps warming (and growing) for minutes after the
# bed sensor reads the target, so a Z check made at once is a little off.
#
# BED_SOAK_CALIBRATE BED=80 [POINTS=5|1] [NOZZLE=140] [INTERVAL=60]
#     [STABLE=0.005] [WINDOW=120] [MAX=1500] [FORCE=1]
#   From a cold bed: home, nozzle to NOZZLE (a hot nozzle grows too, so it
#   stays constant), bed to BED, then probe every INTERVAL seconds, at the
#   centre and (POINTS=5) 30 mm in from each corner: the heater warms the
#   middle first, so the centre domes and the corners lag. Ends when every
#   point has stayed within STABLE mm for WINDOW seconds (or after MAX).
#   Saves, per bed temperature (save variable ad5x_bed_soak): settle (the
#   slowest point's time from the bed reaching BED until it stayed within
#   STABLE of its final value), drift (the centre's total change), warp
#   (how much the corners moved relative to the centre: the shape change),
#   from (the starting temperature), date. Heaters off at the end.
# BED_SOAK_START BED= FROM= [SECONDS=] [PER_DEGREE=3] [MAX=300] [MODE=]
#   PRINT_START, when the bed has reached BED (FROM: its temperature when
#   the print started). The soak: SECONDS if given; none when FROM was
#   within 5 C of BED; else the calibrated settle time of the nearest
#   calibrated temperature (within 15 C), scaled by how far the bed rose;
#   else PER_DEGREE seconds per degree risen; at most MAX. MODE=probe:
#   instead of a time, probe until two readings 60 s apart agree within
#   0.005 mm (POINTS=1: the centre, 5: also the corners), at most that time.
#   Two readings can't tell how much is still to come: on a bed settling
#   like a measured one this stops with about 0.01 mm left, and the load
#   cells' own scatter limits it; the calibration is the better guide.
# BED_SOAK_WAIT
#   Waits for what is left of the soak (the purge and brushing since
#   BED_SOAK_START count), with a countdown on the screen.
# printer.ad5x_soak: calibration ({"80": {settle, drift, from, date}}),
#   running, soak (seconds of the current print's soak), last (readings of
#   the last calibration: [[seconds, z centre, z corners...], ...]).
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import time

VARIABLE = "ad5x_bed_soak"
CENTRE = (107.5, 107.5)
# Centre first, then 30 mm in from each corner (bed 0-215 x 0-215)
POINTS5 = (CENTRE, (30., 30.), (185., 30.), (185., 185.), (30., 185.))
NEAREST = 15.   # C: a calibration this close to the target is used
HOT = 5.        # C: a bed this close to the target at the start needs none


def settle_time(readings, stable):
    """Seconds from the first reading until Z stayed within stable of the
    last reading (readings: [(seconds, z)])."""
    if not readings:
        return 0.
    final = readings[-1][1]
    settle = readings[-1][0]
    for t, z in reversed(readings):
        if abs(z - final) > stable:
            break
        settle = t
    return settle


def is_stable(readings, stable, window):
    """Z within stable over the last window seconds (and that long run)."""
    if not readings or readings[-1][0] - readings[0][0] < window:
        return False
    end = readings[-1][0]
    zs = [z for t, z in readings if t >= end - window]
    return len(zs) >= 2 and max(zs) - min(zs) <= stable


def soak_seconds(bed, start, calibration, per_degree, max_s):
    """Soak for a print heating the bed from start to bed (see header)."""
    rise = bed - start
    if rise <= HOT:
        return 0., "bed already hot"
    near = None
    for key, cal in (calibration or {}).items():
        try:
            t = float(key)
        except ValueError:
            continue
        if abs(t - bed) <= NEAREST and (near is None or
                                        abs(t - bed) < abs(near[0] - bed)):
            near = (t, cal)
    if near is not None:
        t, cal = near
        cal_rise = max(t - float(cal.get('from', 20.)), 1.)
        s = float(cal.get('settle', 0.)) * min(rise / cal_rise, 2.)
        return min(s, max_s), "calibrated at %d C" % (t,)
    return min(rise * per_degree, max_s), "%.0f s per degree" % (per_degree,)


class BedSoak:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.calibration = {}
        self.running = False
        self.last = []
        self.soak = 0.
        self.until = 0.
        self.mode = "time"
        self.points = 1
        self.printer.register_event_handler("klippy:connect", self._load)
        for cmd, desc in (
                ("BED_SOAK_CALIBRATE", "Measure how long the bed's Z keeps "
                 "moving after heating: BED= (from a cold bed)"),
                ("BED_SOAK_START", "PRINT_START: decide the bed soak: BED= "
                 "FROM= [SECONDS=]"),
                ("BED_SOAK_WAIT", "PRINT_START: wait for the rest of the "
                 "bed soak")):
            self.gcode.register_command(cmd, getattr(self, "cmd_" + cmd),
                                        desc=desc)

    def _load(self):
        sv = self.printer.lookup_object('save_variables', None)
        v = sv.allVariables.get(VARIABLE) if sv is not None else None
        if isinstance(v, dict):
            self.calibration = {str(k): c for k, c in v.items()
                                if isinstance(c, dict)}

    def _save(self):
        if self.printer.lookup_object('save_variables', None) is None:
            return
        self.gcode.run_script_from_command(
            "SAVE_VARIABLE VARIABLE=%s VALUE=\"%r\"" % (VARIABLE,
                                                        self.calibration))

    def _status(self, msg):
        self.gcode.run_script_from_command('_PRINT_STATUS MSG="%s"' % (msg,))

    def _sleep(self, seconds):
        end = self.reactor.monotonic() + seconds
        while not self.printer.is_shutdown():
            now = self.reactor.monotonic()
            if now >= end:
                return
            self.reactor.pause(min(end, now + 1.))
        raise self.gcode.error("Shutdown during the bed soak")

    def _temp(self, name):
        heater = self.printer.lookup_object(name)
        return heater.get_status(self.reactor.monotonic())['temperature']

    def _probe_at(self, xy):
        self.gcode.run_script_from_command(
            "G90\nG1 Z5 F800\nG1 X%.1f Y%.1f F30000\nWEIGHT_TARE\nPROBE\n"
            "G1 Z5 F800" % xy)
        probe = self.printer.lookup_object('probe')
        st = probe.get_status(self.reactor.monotonic())
        return st['last_probe_position'][2]

    def _probe_points(self, n):
        return [self._probe_at(xy) for xy in (POINTS5 if n == 5
                                              else POINTS5[:1])]

    # Calibration
    def cmd_BED_SOAK_CALIBRATE(self, gcmd):
        bed = gcmd.get_float('BED', minval=40., maxval=110.)
        npts = gcmd.get_int('POINTS', 5)
        if npts not in (1, 5):
            raise gcmd.error("POINTS is 1 or 5")
        nozzle = gcmd.get_float('NOZZLE', 140., minval=0., maxval=200.)
        interval = gcmd.get_float('INTERVAL', 60. if npts == 5 else 30.,
                                  minval=10.)
        stable = gcmd.get_float('STABLE', .005, above=0.)
        window = gcmd.get_float('WINDOW', 120., minval=interval)
        max_s = gcmd.get_float('MAX', 1500., minval=window)
        start = self._temp('heater_bed')
        if start > 40. and not gcmd.get_int('FORCE', 0):
            raise gcmd.error("The bed is at %.0f C: start from a cold bed "
                             "(below 40 C) for real numbers, or FORCE=1"
                             % (start,))
        self.running = True
        self.last = []
        readings = [[] for _ in range(npts)]
        try:
            gcmd.respond_info("Bed soak calibration at %.0f C (from %.0f C):"
                              " nozzle %.0f C, probing %s every %.0f s until"
                              " Z stays within %.3f mm for %.0f s"
                              % (bed, start, nozzle, "the centre and corners"
                                 if npts == 5 else "the centre", interval,
                                 stable, window))
            self.gcode.run_script_from_command("G28")
            self._status("Bed soak test: heating nozzle")
            self.gcode.run_script_from_command(
                "G90\nG1 X%.1f Y%.1f Z10 F30000\nM109 S%.0f" % (CENTRE + (nozzle,)))
            self.gcode.run_script_from_command("M140 S%.0f" % (bed,))
            while self._temp('heater_bed') < bed - 1.:
                self._status("Bed soak test: bed %.0f / %.0f C"
                             % (self._temp('heater_bed'), bed))
                self._sleep(5.)
            t0 = self.reactor.monotonic()
            while True:
                t = self.reactor.monotonic() - t0
                zs = self._probe_points(npts)
                for r, z in zip(readings, zs):
                    r.append((round(t, 1), round(z, 4)))
                self.last.append([round(t, 1)] + [round(z, 4) for z in zs])
                d = [z - r[0][1] for z, r in zip(zs, readings)]
                gcmd.respond_info("%4d s: centre %+.4f%s (since the bed was "
                                  "hot)" % (t, d[0], "" if npts == 1 else
                                            ", corners " + " ".join(
                                                "%+.4f" % x for x in d[1:])))
                self._status("Bed soak test: %d s, centre %+.3f" % (t, d[0]))
                if all(is_stable(r, stable, window) for r in readings) \
                        or t >= max_s:
                    break
                self._sleep(max(0., t0 + t + interval
                                - self.reactor.monotonic()))
        finally:
            self.running = False
            self.gcode.run_script_from_command("M140 S0\nM104 S0")
            self._status("")
        if not readings[0]:
            return
        settle = max(settle_time(r, stable) for r in readings)
        change = [r[-1][1] - r[0][1] for r in readings]
        warp = max([abs(c - change[0]) for c in change[1:]] or [0.])
        done = all(is_stable(r, stable, window) for r in readings)
        self.calibration["%d" % (round(bed),)] = {
            'settle': round(settle), 'drift': round(change[0], 4),
            'warp': round(warp, 4), 'points': npts, 'from': round(start),
            'stable': done, 'date': time.strftime("%Y-%m-%d")}
        self._save()
        gcmd.respond_info(
            "Bed soak at %.0f C: the centre moved %+.3f mm%s; every point "
            "stayed within %.3f mm after %d s%s. PRINT_START now soaks about "
            "that long (less what the purge takes)."
            % (bed, change[0], "" if npts == 1 else
               ", the corners up to %.3f mm more or less than the centre"
               % (warp,), stable, settle, "" if done else
               " (not settled within MAX: the result is a lower bound)"))

    # Print start
    def cmd_BED_SOAK_START(self, gcmd):
        bed = gcmd.get_float('BED')
        start = gcmd.get_float('FROM', 0.)
        self.mode = gcmd.get('MODE', 'time').lower()
        if self.mode not in ('time', 'probe'):
            raise gcmd.error("MODE is time or probe")
        self.points = gcmd.get_int('POINTS', 1)
        if self.points not in (1, 5):
            raise gcmd.error("POINTS is 1 or 5")
        if gcmd.get('SECONDS', '') != '':
            soak, why = gcmd.get_float('SECONDS', minval=0.), "SOAK="
        else:
            soak, why = soak_seconds(
                bed, start, self.calibration,
                gcmd.get_float('PER_DEGREE', 3., minval=0.),
                gcmd.get_float('MAX', 300., minval=0.))
        self.soak = soak
        self.until = self.reactor.monotonic() + soak
        if soak > 0:
            gcmd.respond_info("Bed heat soak: %s%d s (%s)" % (
                "up to " if self.mode == 'probe' else "", soak, why))

    def cmd_BED_SOAK_WAIT(self, gcmd):
        if self.soak <= 0:
            return
        if self.mode == 'probe':
            self._probe_until_stable(gcmd)
            return
        while True:
            left = self.until - self.reactor.monotonic()
            if left < 1.:
                break
            self._status("Bed heat soak %d:%02d" % (left // 60, left % 60))
            self._sleep(min(left, 5.))
        self.soak = 0.

    def _probe_until_stable(self, gcmd, stable=.005, interval=60.):
        prev = self._probe_points(self.points)
        while self.reactor.monotonic() < self.until:
            self._status("Bed heat soak: waiting for Z to settle")
            self._sleep(interval)
            zs = self._probe_points(self.points)
            moved = max(abs(a - b) for a, b in zip(zs, prev))
            if moved <= stable:
                gcmd.respond_info("Bed heat soak: Z settled (at most %.3f mm"
                                  " in %d s)" % (moved, interval))
                break
            prev = zs
        self.soak = 0.

    def get_status(self, eventtime):
        return {'calibration': self.calibration, 'running': self.running,
                'soak': self.soak, 'last': self.last}


def load_config(config):
    return BedSoak(config)
