# Plugins: optional bundles of Klipper config (and Python extras, and a
# Moonraker part), switched on and off per printer
#
# A plugin is a directory <name>/ with plugin.json (metadata), plugin.cfg
# (Klipper config), README.md and optionally extras/*.py (Klipper modules)
# and moonraker.conf (Moonraker sections, e.g. its own [update_manager]).
# Shipped plugins come with the system image (shipped_dir, read-only,
# updated with the image); other people's and the user's own go in
# user_dir (never touched by system updates; a user plugin with a shipped
# plugin's name replaces it). Which plugins are on is kept only in the
# printer's own plugins.cfg (config dir), one [include] line each, which
# ad5x.cfg reads. The include paths are glob patterns ("plugi[n].cfg"): a
# plugin that disappears is skipped instead of stopping Klipper.
#
# ENABLE_PLUGIN NAME= / DISABLE_PLUGIN NAME= (zMod's command names) edit
# plugins.cfg and restart Klipper; LIST_PLUGINS shows them. A plugin is
# refused when its requires_os (plugin API version) doesn't fit this
# system's PLUGIN_API_VERSION, when a plugin it requires is off, or when a
# conflicting one is on.
#
# Extras: Klipper loads modules only from klippy/extras (read-only image).
# This module, loaded before the plugins' sections (ad5x.cfg declares it
# before including plugins.cfg), imports each enabled plugin's
# extras/<module>.py as extras.<module> and creates the objects for its
# config sections the way Klipper's load_object does. Only enabled,
# compatible plugins' code is loaded; a module name Klipper already has is
# refused. No Klipper change needed.
#
# Moonraker: run as a script (S62moonraker does, before Moonraker starts)
# it writes moonraker-plugins.conf, the [include] list of the enabled
# plugins' moonraker.conf files; Klipper rewrites it when plugins change.
# Moonraker reads it at its next start. See docs/plugins.md and
# docs/plugin-api.md.
#
# Copyright (C) 2026  ad5x-open contributors
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import importlib.util
import json
import logging
import os
import re
import sys

# The plugin API this system offers (docs/plugin-api.md): major.minor.
# Minor: additions only. Major: something plugins may use changed or went.
# post-build.sh copies it to /usr/lib/os-release as AD5X_PLUGIN_API.
PLUGIN_API_VERSION = "1.2"

CONFIG_DIR = "/home/klipper/printer_data/config"
SHIPPED_DIR = "/usr/share/ad5x/plugins"
USER_DIR = "/data/ad5x/plugins"

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")
# [include <dir>/<name>/plugin.cfg], with or without the glob brackets
INCLUDE_RE = re.compile(
    r"^\s*\[include\s+(?P<path>\S*/(?P<name>[A-Za-z0-9_.-]+)/"
    r"plugi(?:n|\[n\])\.cfg)\s*\]\s*$")
# print_stats states during which plugins can't be switched (it restarts)
BUSY_STATES = ("printing", "paused")

PLUGINS_HEADER = """\
# Plugins enabled on this printer (docs/plugins.md). Written by
# ENABLE_PLUGIN / DISABLE_PLUGIN; hand edits are kept. One [include] line
# per plugin; the [n] makes the path a pattern, so a plugin that is gone
# is skipped instead of stopping Klipper. System updates never change
# this file.
"""

MOONRAKER_HEADER = """\
# Moonraker parts of the enabled plugins (docs/plugins.md). Generated from
# plugins.cfg when Moonraker starts and when plugins change; don't edit.
# Moonraker reads it after moonraker.conf (S62moonraker).
"""

def parse_version(text):
    """'1.2' -> (1, 2); None if not major.minor numbers."""
    m = re.match(r"^\s*(\d+)\.(\d+)\s*$", str(text or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None

def api_compatible(required, offered=PLUGIN_API_VERSION):
    """Same major version, offered minor at least the required one.
    No requirement given: compatible."""
    if required in (None, ""):
        return True
    req, have = parse_version(required), parse_version(offered)
    return bool(req and have and req[0] == have[0] and req[1] <= have[1])

def read_metadata(plugin_dir, name):
    """plugin.json as a dict with every field present; 'error' set when
    the file is unusable (the plugin can't be enabled then)."""
    meta = {'name': name, 'description': "", 'version': "", 'author': "",
            'url': "", 'requires_os': "", 'requires': [], 'conflicts': [],
            'error': None}
    path = os.path.join(plugin_dir, 'plugin.json')
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
    except FileNotFoundError:
        meta['error'] = "no plugin.json"
        return meta
    except (OSError, ValueError) as e:
        meta['error'] = "plugin.json: %s" % (e,)
        return meta
    for key in ('description', 'version', 'author', 'url', 'requires_os'):
        if data.get(key) is not None:
            meta[key] = str(data[key])
    for key in ('requires', 'conflicts'):
        val = data.get(key) or []
        if isinstance(val, str):
            val = [v.strip() for v in val.split(",")]
        meta[key] = [str(v).strip().lower() for v in val if str(v).strip()]
    if data.get('name') not in (None, name):
        meta['error'] = "plugin.json name '%s' differs from the directory" % (
            data.get('name'),)
    elif meta['requires_os'] and parse_version(meta['requires_os']) is None:
        meta['error'] = "requires_os '%s' is not major.minor" % (
            meta['requires_os'],)
    return meta

def scan(shipped_dir=SHIPPED_DIR, user_dir=USER_DIR):
    """name -> info for every directory holding a plugin.cfg; user plugins
    replace shipped ones of the same name."""
    found = {}
    for source, base in (("shipped", shipped_dir), ("user", user_dir)):
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for name in names:
            d = os.path.join(base, name)
            if not NAME_RE.match(name) or not os.path.isfile(
                    os.path.join(d, 'plugin.cfg')):
                continue
            info = read_metadata(d, name)
            info.update({
                'dir': d, 'source': source,
                'compatible': api_compatible(info['requires_os']),
                'extras': os.path.isdir(os.path.join(d, 'extras')),
                'moonraker': os.path.isfile(os.path.join(d,
                                                         'moonraker.conf'))})
            found[name] = info
    return found

def read_enabled(plugins_file):
    """(enabled names in file order, lines); a missing file is empty
    (lines None)."""
    try:
        with open(plugins_file) as f:
            lines = f.read().splitlines()
    except OSError:
        return [], None
    names = []
    for line in lines:
        m = INCLUDE_RE.match(line)
        if m is not None and m.group('name') not in names:
            names.append(m.group('name'))
    return names, lines

def moonraker_text(names, found):
    lines = [MOONRAKER_HEADER.rstrip("\n")]
    updates = False
    for name in names:
        info = found.get(name)
        if info is None or not info['moonraker'] or not info['compatible'] \
                or info['error']:
            continue
        path = os.path.join(info['dir'], 'moonraker.conf')
        try:
            with open(path) as f:
                updates |= "[update_manager" in f.read()
        except OSError:
            continue
        lines.append("[include %s]" % (path,))
    if updates:
        # Plugins kept up to date by Moonraker: this system has no package
        # manager for Moonraker's system updates.
        lines += ["[update_manager]", "enable_system_updates: False"]
    return "\n".join(lines) + "\n"

def write_if_changed(path, text):
    """Write text atomically unless the file already holds it. True if
    written."""
    try:
        with open(path) as f:
            if f.read() == text:
                return False
    except OSError:
        pass
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(text)
    os.replace(tmp, path)
    return True

class AD5XPlugins:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.plugins_file = config.get(
            'plugins_file', os.path.join(CONFIG_DIR, 'plugins.cfg'))
        self.moonraker_file = config.get(
            'moonraker_file', os.path.join(CONFIG_DIR,
                                           'moonraker-plugins.conf'))
        self.shipped_dir = config.get('shipped_dir', SHIPPED_DIR)
        self.user_dir = config.get('user_dir', USER_DIR)
        self.found = scan(self.shipped_dir, self.user_dir)
        # Enabled at this start (plugins.cfg as Klipper read it)
        self.loaded = read_enabled(self.plugins_file)[0]
        self.warnings = []
        self.modules = {}
        self._load_extras(config)
        self.printer.register_event_handler("klippy:ready",
                                            self._handle_ready)
        # Also while Klipper isn't ready: a plugin whose config stops
        # Klipper can be disabled from the console (when the error comes
        # after this section, as a plugin's own sections do)
        for cmd in ("ENABLE_PLUGIN", "DISABLE_PLUGIN", "LIST_PLUGINS"):
            self.gcode.register_command(cmd, getattr(self, "cmd_" + cmd),
                                        when_not_ready=True,
                                        desc=getattr(self, "cmd_%s_help" % cmd))
    # Startup
    def _warn(self, msg):
        logging.warning("ad5x_plugins: %s", msg)
        self.warnings.append(msg)
        pconfig = self.printer.lookup_object('configfile', None)
        if pconfig is not None and hasattr(pconfig, 'runtime_warning'):
            pconfig.runtime_warning(msg)
    def _usable(self, name):
        """Enabled plugin whose code may run: present, valid, compatible."""
        info = self.found.get(name)
        if info is None:
            self._warn("Plugin %s is enabled but missing (no plugin.cfg in "
                       "%s or %s); skipped" % (name, self.shipped_dir,
                                               self.user_dir))
            return None
        if info['error']:
            self._warn("Plugin %s: %s; its extras are not loaded"
                       % (name, info['error']))
            return None
        if not info['compatible']:
            self._warn("Plugin %s needs plugin API %s, this system has %s; "
                       "its extras are not loaded (DISABLE_PLUGIN NAME=%s)"
                       % (name, info['requires_os'], PLUGIN_API_VERSION,
                          name))
            return None
        return info
    def _load_extras(self, config):
        core = os.path.dirname(os.path.abspath(__file__))
        wanted = {}
        for name in self.loaded:
            info = self._usable(name)
            if info is None or not info['extras']:
                continue
            ext = os.path.join(info['dir'], 'extras')
            for fn in sorted(os.listdir(ext)):
                mod = fn[:-3]
                if not fn.endswith('.py') or not MODULE_RE.match(mod):
                    continue
                if os.path.exists(os.path.join(core, fn)) or os.path.isdir(
                        os.path.join(core, mod)):
                    raise config.error(
                        "Plugin %s: extras/%s has the name of a Klipper "
                        "module; rename it" % (name, fn))
                if mod in wanted:
                    raise config.error(
                        "Plugins %s and %s both have extras/%s"
                        % (wanted[mod][0], name, fn))
                wanted[mod] = (name, os.path.join(ext, fn))
        for mod, (name, path) in sorted(wanted.items()):
            full = 'extras.' + mod
            spec = importlib.util.spec_from_file_location(full, path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[full] = module
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                del sys.modules[full]
                logging.exception("ad5x_plugins: loading %s", path)
                raise config.error("Plugin %s: extras/%s.py failed to load: "
                                   "%s" % (name, mod, e))
            self.modules[mod] = module
            logging.info("ad5x_plugins: loaded %s from plugin %s", mod, name)
        # Objects for the plugin modules' config sections, as load_object
        # would make them (it only looks in klippy/extras)
        for section in config.get_prefix_sections(''):
            sname = section.get_name()
            parts = sname.split()
            module = self.modules.get(parts[0])
            if module is None or self.printer.lookup_object(
                    sname, None) is not None:
                continue
            init = getattr(module, 'load_config_prefix' if len(parts) > 1
                           else 'load_config', None)
            if init is None:
                raise config.error("Unable to load module '%s'" % (sname,))
            self.printer.add_object(sname, init(config.getsection(sname)))
    def _handle_ready(self):
        # Keep the Moonraker list in step (a system update may have added
        # or dropped a plugin's moonraker.conf). Moonraker reads it at its
        # next start.
        self._write_moonraker(self.loaded)
    def _write_moonraker(self, names):
        try:
            return write_if_changed(self.moonraker_file,
                                    moonraker_text(names, self.found))
        except OSError as e:
            logging.info("ad5x_plugins: can't write %s: %s",
                         self.moonraker_file, e)
            return False
    # plugins.cfg
    def _write_enabled(self, enable=(), disable=()):
        """Add include lines for enable, drop the lines of disable (and
        duplicate lines of any plugin); other lines are kept as they are."""
        lines = read_enabled(self.plugins_file)[1]
        if lines is None:
            lines = PLUGINS_HEADER.splitlines()
        out, seen = [], set()
        for line in lines:
            m = INCLUDE_RE.match(line)
            if m is not None:
                name = m.group('name')
                if name in disable or name in seen:
                    continue
                seen.add(name)
            out.append(line)
        for name in enable:
            if name not in seen:
                out.append("[include %s/plugi[n].cfg]"
                           % (self.found[name]['dir'],))
        write_if_changed(self.plugins_file, "\n".join(out) + "\n")
        return read_enabled(self.plugins_file)[0]
    # Commands
    def _check_idle(self, gcmd):
        ps = self.printer.lookup_object('print_stats', None)
        if ps is not None and ps.get_status(
                self.printer.get_reactor().monotonic()).get(
                    'state') in BUSY_STATES:
            raise gcmd.error("Plugins can't be switched during a print "
                             "(Klipper restarts)")
    def _apply(self, gcmd, enable=(), disable=()):
        try:
            names = self._write_enabled(enable, disable)
        except OSError as e:
            raise gcmd.error("Can't write %s: %s" % (self.plugins_file, e))
        if self._write_moonraker(names):
            gcmd.respond_info("The Moonraker part changes when Moonraker "
                              "restarts (reboot)")
        if gcmd.get_int('RESTART', 1):
            gcmd.respond_info("Restarting Klipper")
            self.gcode.run_script_from_command("RESTART")
        else:
            gcmd.respond_info("Takes effect at the next RESTART")
    cmd_ENABLE_PLUGIN_help = ("Enable a plugin and restart Klipper: NAME= "
                              "[RESTART=0]")
    def cmd_ENABLE_PLUGIN(self, gcmd):
        self.found = scan(self.shipped_dir, self.user_dir)
        name = gcmd.get('NAME').strip().lower()
        info = self.found.get(name)
        if info is None:
            raise gcmd.error("Unknown plugin '%s'. Available: %s" % (
                name, ", ".join(sorted(self.found)) or "none"))
        enabled = read_enabled(self.plugins_file)[0]
        if name in enabled:
            gcmd.respond_info("Plugin %s is already enabled" % (name,))
            return
        if info['error']:
            raise gcmd.error("Plugin %s: %s" % (name, info['error']))
        if not info['compatible']:
            raise gcmd.error("Plugin %s needs plugin API %s; this system "
                             "has %s" % (name, info['requires_os'],
                                         PLUGIN_API_VERSION))
        missing = [r for r in info['requires'] if r not in enabled]
        if missing:
            raise gcmd.error("Plugin %s needs %s: enable it first" % (
                name, ", ".join(missing)))
        clash = [c for c in enabled if c in info['conflicts'] or name in
                 self.found.get(c, {}).get('conflicts', ())]
        if clash:
            raise gcmd.error("Plugin %s can't be on together with %s: "
                             "disable it first" % (name, ", ".join(clash)))
        self._check_idle(gcmd)
        gcmd.respond_info("Plugin %s %s enabled (%s)" % (
            name, info['version'], info['source']))
        self._apply(gcmd, enable=[name])
    cmd_DISABLE_PLUGIN_help = ("Disable a plugin and restart Klipper: NAME= "
                               "[RESTART=0]")
    def cmd_DISABLE_PLUGIN(self, gcmd):
        self.found = scan(self.shipped_dir, self.user_dir)
        name = gcmd.get('NAME').strip().lower()
        enabled = read_enabled(self.plugins_file)[0]
        if name not in enabled:
            if name not in self.found:
                raise gcmd.error("Unknown plugin '%s'" % (name,))
            gcmd.respond_info("Plugin %s is not enabled" % (name,))
            return
        users = [n for n in enabled if n != name
                 and name in self.found.get(n, {}).get('requires', ())]
        if users:
            raise gcmd.error("Plugin %s is needed by %s: disable that first"
                             % (name, ", ".join(users)))
        self._check_idle(gcmd)
        gcmd.respond_info("Plugin %s disabled" % (name,))
        self._apply(gcmd, disable=[name])
    cmd_LIST_PLUGINS_help = "List the plugins (shipped and own) and which are on"
    def cmd_LIST_PLUGINS(self, gcmd):
        self.found = scan(self.shipped_dir, self.user_dir)
        enabled = read_enabled(self.plugins_file)[0]
        lines = ["Plugin API %s" % (PLUGIN_API_VERSION,)]
        for name in sorted(set(self.found) | set(enabled)):
            info = self.found.get(name)
            on = name in enabled
            if info is None:
                lines.append("[on]  %s: missing, skipped" % (name,))
                continue
            notes = []
            if info['error']:
                notes.append(info['error'])
            elif not info['compatible']:
                notes.append("needs plugin API %s" % (info['requires_os'],))
            if info['requires']:
                notes.append("requires " + ", ".join(info['requires']))
            if info['conflicts']:
                notes.append("conflicts with " + ", ".join(info['conflicts']))
            if on != (name in self.loaded):
                notes.append("until RESTART")
            lines.append("%s %s %s (%s%s): %s%s" % (
                "[on] " if on else "[off]", name, info['version'] or "-",
                info['source'], ", " + info['author'] if info['author']
                else "", info['description'] or "-",
                " [%s]" % ("; ".join(notes),) if notes else ""))
        lines.append("ENABLE_PLUGIN NAME=<name> / DISABLE_PLUGIN NAME=<name>")
        gcmd.respond_info("\n".join(lines))
    def get_status(self, eventtime):
        return {
            'api_version': PLUGIN_API_VERSION,
            'enabled': list(self.loaded),
            'available': {
                n: {k: i[k] for k in ('source', 'description', 'version',
                                      'author', 'url', 'requires_os',
                                      'compatible')}
                for n, i in self.found.items()},
            'warnings': list(self.warnings)}

def load_config(config):
    return AD5XPlugins(config)

def main(argv):
    """S62moonraker: write the Moonraker include list before Moonraker
    starts. usage: ad5x_plugins.py moonraker [PLUGINS_CFG [OUT]]"""
    if len(argv) < 2 or argv[1] != "moonraker":
        sys.stderr.write("usage: ad5x_plugins.py moonraker [PLUGINS_CFG "
                         "[OUT]]\n")
        return 2
    plugins_file = argv[2] if len(argv) > 2 else os.path.join(
        CONFIG_DIR, 'plugins.cfg')
    out = argv[3] if len(argv) > 3 else os.path.join(
        CONFIG_DIR, 'moonraker-plugins.conf')
    names = read_enabled(plugins_file)[0]
    found = scan(SHIPPED_DIR, USER_DIR)
    write_if_changed(out, moonraker_text(names, found))
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
