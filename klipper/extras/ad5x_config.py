# The printer's editable macros (macros/*.cfg in the config directory):
# update notices and the backups of edited files
#
# The macros/ files are copied from the image's templates
# (/usr/share/ad5x/defaults/macros) by the boot script ad5x-config-templates
# (S05ad5x-data). When an update brings a changed template, that script
# replaces the printer's file; an edited one is first kept as
# <name>.cfg.bak-<date> and a line is added to config-updates.txt in the
# config directory (docs/config-layout.md). This module tells the user:
# at Klipper start the notice lines go to the console (and a short message
# to the screen) while that file exists; CONFIG_BACKUPS lists the notices
# and the backup files, CONFIG_BACKUPS ACK=1 removes the notice (backups
# stay until deleted in Fluidd).
#
# Copyright (C) 2026  ad5x-open contributors
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging
import os
import re

CONFIG_DIR = "/home/klipper/printer_data/config"
NOTICE_FILE = "config-updates.txt"
BACKUP_RE = re.compile(r"^(?P<name>.+\.cfg)\.bak-(?P<stamp>[0-9-]+)$")


class AD5XConfig:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.config_dir = config.get('config_dir', CONFIG_DIR)
        self.notice_path = os.path.join(self.config_dir, NOTICE_FILE)
        self.macros_dir = os.path.join(self.config_dir, 'macros')
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_command('CONFIG_BACKUPS', self.cmd_CONFIG_BACKUPS,
                                    desc=self.cmd_CONFIG_BACKUPS_help)
        self.status = {'notices': [], 'backups': []}
        self.printer.register_event_handler("klippy:ready", self._ready)
    def _refresh(self):
        self.status = {'notices': self._notices(),
                       'backups': self._backups()}
        return self.status
    def _notices(self):
        try:
            with open(self.notice_path) as f:
                return [l.rstrip('\n') for l in f if l.strip()]
        except OSError:
            return []
    def _backups(self):
        try:
            names = os.listdir(self.macros_dir)
        except OSError:
            return []
        return sorted('macros/' + n for n in names if BACKUP_RE.match(n))
    def _ready(self):
        notices = self._refresh()['notices']
        if not notices:
            return
        for line in notices:
            logging.info("ad5x_config: %s", line)
        reactor = self.printer.get_reactor()
        reactor.register_callback(lambda et: self._announce(notices))
    def _announce(self, notices):
        lines = ["Macros updated by a system update:"] + notices + [
            "Merge your changes from the .bak file (Fluidd, Configuration),"
            " lasting ones into local.cfg. CONFIG_BACKUPS ACK=1 hides this."]
        self.gcode.respond_info("\n".join(lines))
        try:
            self.gcode.run_script("M117 Macros updated: see CONFIG_BACKUPS")
        except Exception:
            logging.exception("ad5x_config: M117")
    cmd_CONFIG_BACKUPS_help = ("List macros/ files an update replaced and "
                               "the backups of edited ones; ACK=1 clears "
                               "the notice")
    def cmd_CONFIG_BACKUPS(self, gcmd):
        ack = gcmd.get_int('ACK', 0)
        notices = self._notices()
        backups = self._backups()
        lines = []
        if notices:
            lines.append("Update notices (%s):" % (NOTICE_FILE,))
            lines.extend("  " + l for l in notices)
        else:
            lines.append("No update notices.")
        if backups:
            lines.append("Backups of edited macros files (delete them in "
                         "Fluidd when merged):")
            lines.extend("  " + b for b in backups)
        else:
            lines.append("No backups in macros/.")
        if ack and notices:
            try:
                os.remove(self.notice_path)
                lines.append("Notice cleared (backups kept).")
            except OSError as e:
                raise gcmd.error("CONFIG_BACKUPS: can't remove %s: %s"
                                 % (self.notice_path, e))
        self._refresh()
        gcmd.respond_info("\n".join(lines))
    def get_status(self, eventtime):
        return dict(self.status)


def load_config(config):
    return AD5XConfig(config)
