# The AD5X speaker: beeps (M300), MIDI files (PLAY_MIDI, zMod's name) and
# sounds on print events, played by /usr/bin/ad5x-sound in the background
#
# M300 [S<Hz>] [P<ms>]          a beep (default 1000 Hz, 100 ms)
# PLAY_MIDI FILE=<name.mid>     a MIDI file from the printer's config folder
#                               midi/ (yours) or the image's sounds
# PLAY_SOUND EVENT=<event>      what that event plays
# SOUND_STOP
# SOUND_SETUP [ENABLE=0|1] [VOLUME=0-100] [<EVENT>=<file>|0]   no
#     parameters: list the settings and the sound files
# Events: startup, start (print started), complete, error (failed or
# Klipper shut down), cancelled, paused (runout, IFS problem, ...),
# refill (IFS auto-refill switched slots). <EVENT>=0 silences one.
# Settings: save variable ad5x_sound. printer.ad5x_sound: speaker (the image
# found one), enabled, volume, events, files, playing.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import os
import subprocess

VARIABLE = "ad5x_sound"
PLAYER = "/usr/bin/ad5x-sound"
SPEAKER_CONF = "/run/ad5x-sound.conf"
SHIPPED = "/usr/share/ad5x/sounds"
USER = "/home/klipper/printer_data/config/midi"
EVENTS = ("startup", "start", "complete", "error", "cancelled", "paused",
          "refill")
DEFAULTS = {"startup": "", "start": "start.mid", "complete": "complete.mid",
            "error": "error.mid", "cancelled": "", "paused": "paused.mid",
            "refill": "refill.mid"}
# print_stats state -> event
STATE_EVENTS = {"printing": "start", "complete": "complete", "error": "error",
                "cancelled": "cancelled", "paused": "paused"}


class AD5XSound:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.gcode = self.printer.lookup_object('gcode')
        self.player = config.get('player', PLAYER)
        self.shipped_dir = config.get('shipped_dir', SHIPPED)
        self.user_dir = config.get('user_dir', USER)
        self.speaker = os.path.exists(config.get('speaker_conf',
                                                 SPEAKER_CONF))
        self.enabled = True
        self.volume = 70
        self.events = dict(DEFAULTS)
        self.proc = None
        self.state = None
        self.refill = None
        self.printer.register_event_handler("klippy:connect", self._load)
        self.printer.register_event_handler("klippy:ready", self._ready)
        self.printer.register_event_handler("klippy:shutdown",
                                            lambda: self.play_event("error"))
        for cmd, desc in (
                ("M300", "Beep: S=Hz P=ms"),
                ("PLAY_MIDI", "Play a MIDI file: FILE="),
                ("PLAY_SOUND", "Play an event's sound: EVENT="),
                ("SOUND_STOP", "Stop the sound"),
                ("SOUND_SETUP", "Speaker settings: ENABLE= VOLUME= "
                 "<EVENT>=<file>|0")):
            self.gcode.register_command(cmd, getattr(self, "cmd_" + cmd),
                                        desc=desc)

    # Settings
    def _load(self):
        sv = self.printer.lookup_object('save_variables', None)
        v = sv.allVariables.get(VARIABLE) if sv is not None else None
        if not isinstance(v, dict):
            return
        if isinstance(v.get('enabled'), bool):
            self.enabled = v['enabled']
        if isinstance(v.get('volume'), int):
            self.volume = max(0, min(100, v['volume']))
        for e in EVENTS:
            if isinstance(v.get('events', {}).get(e), str):
                self.events[e] = v['events'][e]

    def _save(self):
        if self.printer.lookup_object('save_variables', None) is None:
            return
        val = {'enabled': self.enabled, 'volume': self.volume,
               'events': self.events}
        self.gcode.run_script_from_command(
            "SAVE_VARIABLE VARIABLE=%s VALUE=\"%r\"" % (VARIABLE, val))

    def files(self):
        names = set()
        for d in (self.shipped_dir, self.user_dir):
            try:
                names |= {f for f in os.listdir(d)
                          if f.lower().endswith(('.mid', '.midi'))}
            except OSError:
                pass
        return sorted(names)

    def find(self, name):
        name = os.path.basename(name or "")
        for d in (self.user_dir, self.shipped_dir):
            p = os.path.join(d, name)
            if name and os.path.isfile(p):
                return p
        return None

    # Playing
    def _run(self, args):
        if not self.speaker or not self.enabled:
            return False
        self.stop()
        try:
            self.proc = subprocess.Popen(
                [self.player] + args + ["--volume", str(self.volume)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, close_fds=True)
        except OSError as e:
            logging.info("ad5x_sound: %s", e)
            return False
        return True

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(.5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        self.proc = None

    def play_file(self, name):
        path = self.find(name)
        return path is not None and self._run(["play", path])

    def play_event(self, event):
        name = self.events.get(event)
        if name:
            self.play_file(name)

    # Print events
    def _ready(self):
        self.play_event("startup")
        self.reactor.register_timer(self._watch, self.reactor.NOW)

    def _watch(self, eventtime):
        ps = self.printer.lookup_object('print_stats', None)
        if ps is not None:
            state = ps.get_status(eventtime).get('state')
            if state != self.state:
                if self.state is not None and state in STATE_EVENTS and \
                        not (state == "printing" and self.state == "paused"):
                    self.play_event(STATE_EVENTS[state])
                self.state = state
        ifs = self.printer.lookup_object('ifs', None)
        if ifs is not None:
            refill = ifs.get_status(eventtime).get('refill')
            if refill and refill != self.refill and self.refill is not None:
                self.play_event("refill")
            self.refill = refill or ""
        if self.proc is not None and self.proc.poll() is not None:
            self.proc = None
        return eventtime + 1.

    # Commands
    def cmd_M300(self, gcmd):
        hz = gcmd.get_float('S', 1000., minval=20., maxval=20000.)
        ms = gcmd.get_float('P', 100., minval=0., maxval=10000.)
        if ms > 0:
            self._run(["tone", "%.0f" % hz, "%.0f" % ms])

    def cmd_PLAY_MIDI(self, gcmd):
        name = gcmd.get('FILE', 'complete.mid')
        if self.find(name) is None:
            raise gcmd.error("No MIDI file '%s'. Files: %s (yours go in "
                             "the config folder's midi/)"
                             % (name, ", ".join(self.files()) or "none"))
        if not self.speaker:
            raise gcmd.error("This system found no speaker")
        if not self.enabled:
            gcmd.respond_info("Sound is off (SOUND_SETUP ENABLE=1)")
            return
        self.play_file(name)

    def cmd_PLAY_SOUND(self, gcmd):
        event = gcmd.get('EVENT').lower()
        if event not in EVENTS:
            raise gcmd.error("EVENT is one of " + ", ".join(EVENTS))
        self.play_event(event)

    def cmd_SOUND_STOP(self, gcmd):
        self.stop()

    def cmd_SOUND_SETUP(self, gcmd):
        changed = False
        if gcmd.get('ENABLE', None) is not None:
            self.enabled = gcmd.get_int('ENABLE', minval=0, maxval=1) == 1
            changed = True
        if gcmd.get('VOLUME', None) is not None:
            self.volume = gcmd.get_int('VOLUME', minval=0, maxval=100)
            changed = True
        for e in EVENTS:
            val = gcmd.get(e.upper(), None)
            if val is None:
                continue
            val = "" if val in ("0", "") else os.path.basename(val)
            if val and self.find(val) is None:
                raise gcmd.error("No MIDI file '%s'. Files: %s"
                                 % (val, ", ".join(self.files())))
            self.events[e] = val
            changed = True
        if changed:
            self._save()
        gcmd.respond_info(
            "Speaker: %s, sound %s, volume %d\n%s\nFiles: %s" % (
                "found" if self.speaker else "none found",
                "on" if self.enabled else "off", self.volume,
                "\n".join("  %s: %s" % (e, self.events[e] or "-")
                          for e in EVENTS),
                ", ".join(self.files()) or "none"))

    def get_status(self, eventtime):
        return {'speaker': self.speaker, 'enabled': self.enabled,
                'volume': self.volume, 'events': dict(self.events),
                'files': self.files(),
                'playing': self.proc is not None and self.proc.poll() is None}


def load_config(config):
    return AD5XSound(config)
