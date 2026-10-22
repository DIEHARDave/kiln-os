# Changelog

What changed for people using Kiln OS. Each release's notes (Gitea and
GitHub) take its section from here: `## vX.Y.Z`, or `## Unreleased` when
the release has no section of its own yet (rename it after the release).

## Unreleased

### Added
- **OrcaSlicer filament profiles** (`orca/`): `AD5X PLA`, `AD5X PETG` and
  `AD5X TPU`, starting points with temperatures and volumetric speed limits
  (see `orca/README.md`). Not yet tried in the Orca GUI.

### Changed
- **Setup wizard: Z offset test** checks only the centre, not the whole bed
  (no full-bed mesh); the buttons say **Closer** and **Away** instead of
  `-` and `+`.
- **Setup wizard: purge box** is one row of arrows (Left, Right, Front, Back,
  Factory), so Accept and Abort fit on the page without scrolling. The 0.1 mm
  steps are gone; use 1 mm and Z offset as needed.
- **Setup wizard: bed soak** cools a warm bed first (heater off, up to 15 min
  of waiting, shown on the screen) instead of stopping with "the bed is still
  warm".
- **Setup wizard: IFS tuning** unloads filament left in the toolhead first, when
  the slot is known. If it isn't, the screen says to pull it out by hand, then Retry.

## v0.0.18 (2026-10-22)
### Fixed
- **Home screen: a finger drifting to the edge no longer pages the screen**
  when the arrows page it (resistive touch): the Unload button in the corner
  is pressed reliably. Swiping still works in widget edit mode.
- **Keyboard: the second period on the number page is now an underscore**
  (`_`), for Wi-Fi passwords and commands. The period stays on the row above.
- **The purge box offset applies everywhere**: the box moves at the start
  of a print, the wipe and the nozzle brush used the fixed spot and ignored
  unit.cfg's offset; now every box move uses it (and TRASH_OFFSET's value).
- **Nozzle 10 °C hotter than the file** (245 instead of 235): a file whose
  start line is zMod's `START_PRINT` without `EXTRUDER_TEMP=` (Orca
  profiles that send their own `M104` first) got zMod's default of 245
  for the whole print. `START_PRINT` and `PRINT_START` now keep the
  temperatures the file already set and use the defaults only when it set
  none. Files that give `EXTRUDER_TEMP=` work as before.

### Added
- **Touch screen: purge box check, bed soak and summary steps** in the
  setup wizard, plus the Z offset's load cell estimate (off until
  `zoffset_estimate: 1`), Wi-Fi's Add Hidden Network in the wizard, and
  Settings > Purge Box to move the trash bin.
- **`TRASH_OFFSET X= Y= [RESET=1]`**: moves the purge box (the trash bin)
  from its factory spot (X 52.5, Y 229) and saves it, so it survives
  restarts and updates. X -10 to 10, Y -14 to 2 mm. `RESET=1` goes back to
  the value in unit.cfg. A menu entry and a wizard step can follow.
- **OrcaSlicer printer profiles for every nozzle size** (`orca/`):
  import one per nozzle (0.2 to 1.0 mm) in Orca with File > Import; each
  has the machine G-code and build area. Retraction is from the 0.6 mm
  profile, to be checked on the others (see `orca/README.md`).
- **Recommended OrcaSlicer machine G-code** (`docs/orcaslicer.md`): start,
  end, layer change and colour change G-code to paste into OrcaSlicer's
  printer settings, where the printer does the heating, mesh, first load
  and the purge at the box.

## v0.0.17 (2026-10-22)
### Fixed
- **Home screen: a finger drifting to the edge no longer pages the screen**
  when the arrows page it (resistive touch): the Unload button in the corner
  is pressed reliably. Swiping still works in widget edit mode.
- **Keyboard: the second period on the number page is now an underscore**
  (`_`), for Wi-Fi passwords and commands. The period stays on the row above.
- **The purge box offset applies everywhere**: the box moves at the start
  of a print, the wipe and the nozzle brush used the fixed spot and ignored
  unit.cfg's offset; now every box move uses it (and TRASH_OFFSET's value).
- **Nozzle 10 °C hotter than the file** (245 instead of 235): a file whose
  start line is zMod's `START_PRINT` without `EXTRUDER_TEMP=` (Orca
  profiles that send their own `M104` first) got zMod's default of 245
  for the whole print. `START_PRINT` and `PRINT_START` now keep the
  temperatures the file already set and use the defaults only when it set
  none. Files that give `EXTRUDER_TEMP=` work as before.

### Added
- **Touch screen: purge box check, bed soak and summary steps** in the
  setup wizard, plus the Z offset's load cell estimate (off until
  `zoffset_estimate: 1`), Wi-Fi's Add Hidden Network in the wizard, and
  Settings > Purge Box to move the trash bin.
- **`TRASH_OFFSET X= Y= [RESET=1]`**: moves the purge box (the trash bin)
  from its factory spot (X 52.5, Y 229) and saves it, so it survives
  restarts and updates. X -10 to 10, Y -14 to 2 mm. `RESET=1` goes back to
  the value in unit.cfg. A menu entry and a wizard step can follow.
- **OrcaSlicer printer profiles for every nozzle size** (`orca/`):
  import one per nozzle (0.2 to 1.0 mm) in Orca with File > Import; each
  has the machine G-code and build area. Retraction is from the 0.6 mm
  profile, to be checked on the others (see `orca/README.md`).
- **Recommended OrcaSlicer machine G-code** (`docs/orcaslicer.md`): start,
  end, layer change and colour change G-code to paste into OrcaSlicer's
  printer settings, where the printer does the heating, mesh, first load
  and the purge at the box.

## v0.0.16 (2026-10-21)
### Fixed
- **Nozzle 10 °C hotter than the file** (245 instead of 235): a file whose
  start line is zMod's `START_PRINT` without `EXTRUDER_TEMP=` (Orca
  profiles that send their own `M104` first) got zMod's default of 245
  for the whole print. `START_PRINT` and `PRINT_START` now keep the
  temperatures the file already set and use the defaults only when it set
  none. Files that give `EXTRUDER_TEMP=` work as before.

### Added
- **Recommended OrcaSlicer machine G-code** (`docs/orcaslicer.md`): start,
  end, layer change and colour change G-code to paste into OrcaSlicer's
  printer settings, where the printer does the heating, mesh, first load
  and the purge at the box.

## v0.0.15 (2026-10-21)

### Fixed
- **"WiFi system not ready" on the touch screen**: Wi-Fi now waits longer
  for a slow USB Wi-Fi adapter (10 s instead of 3), and a saved Wi-Fi
  file it can't read (for example one brought over from stock) is put
  aside so Wi-Fi still starts and a network can be joined again. Either
  used to leave the screen's Wi-Fi without its service.
- **A fresh install's first Z offset could overwrite the wizard's.** At
  start-up the offset carried over from stock is copied once; if a
  command was already running then (the setup wizard's Z offset step),
  the copy waited and wrote the old value over the new one afterwards.
  Found by the new emulated wizard test.
- **Setup wizard bed mesh: "Probe samples exceed samples_tolerance"**.
  The mesh step now cleans the nozzle first, as a print does (one touch
  at the bed's front edge, then a scrub along it). Plastic left on the tip
  squashed a little more at every touch, so the probe's three samples
  disagreed.

### Added
- **`logs/wifi.log`** (in Fluidd's log files): what Wi-Fi did at start:
  kernel, adapter driver, number of saved networks (no names or
  passwords), and the exact error if it didn't start. Send it along with
  `helixscreen.log` when Wi-Fi misbehaves.
- **Emulated setup wizard test on a fresh install** in every build: the
  image's own Klipper runs the wizard's steps on a newly installed data
  partition (with a Z offset carried over from stock), and the saved
  results are checked.

## v0.0.14 (2026-10-21)

### Fixed
- **`SAVE_CONFIG` after `PROBE_CALIBRATE`, `Z_OFFSET_APPLY_PROBE` or
  `PID_CALIBRATE`** no longer fails with "conflicts with included value".
  A probe Z offset becomes the printer's saved Z offset (the same first
  layer; the one the touch screen shows and every print uses), and PID or
  input shaper results go to `ad5x-tuning.cfg`, like the setup wizard's.
- **Setup wizard Z offset no longer scrapes the bed**: the test patch now
  starts fresh every time at 0.1 mm, a little high, instead of at the
  offset already saved (which after an install from stock or zMod was
  never tested on Kiln OS). Lower it with - until the lines touch and
  flatten, then Accept.
- **Hidden Wi-Fi networks** saved on the Flashforge screen are found
  now: every saved network is searched for by name (stock saves only the
  name and password). New hidden networks: Settings > Connection > Network
  Settings > Add Hidden Network (the setup wizard lists visible networks
  only).

## v0.0.13 (2026-10-21)

### Fixed
- **Wi-Fi works without Ethernet**: Wi-Fi now always starts, so the
  touch screen can find and join networks and remembers them: in the
  setup wizard, or any time in Settings > Connection > Network Settings.
  Before, a printer installed without Ethernet had no way to get online.
  The networks saved on the Flashforge screen come over on the first
  start.

### Added
- **Wi-Fi switch**: if you only use Ethernet, turn Wi-Fi off in Settings >
  Connection > Network Settings; it stays off after a restart (it comes
  back on by itself only when no Ethernet is connected, so the printer
  can't be cut off).

## v0.0.12 (2026-10-21)

### Changed
- **New home screen on the touch screen**: nozzle and bed temperature,
  fans and notifications along the top, a big print status card (progress,
  file, layer, time left; the last print when idle), and on the right the
  IFS slots, Preheat/Cool Down, the light switch, the live Z offset (tap
  it for baby steps), Motion and Unload (Preheat/Cool Down and Unload are
  greyed out while a print is running or paused). The printer
  picture, temperature graph (tap a temperature to open it) and tips are
  gone. A home screen you never rearranged switches to it with the update;
  one you edited stays as it is.

## v0.0.11 (2026-10-20)

### Added
- **Auto-refill settings**: `IFS_AUTO_REFILL MATCH=exact|similar|any` picks
  how close a backup spool's colour must be (default similar). The printer
  shows which slots back each other up, and a print that loads a slot with
  no backup gets a notice instead of a surprise pause later. A spool put
  in during a print is fed in when a refill needs it.
- **Nozzle size** in the setup wizard (after the time zone) and in
  Settings on the touch screen, or `SET_NOZZLE_SIZE SIZE=0.6`: kept in the
  printer's `nozzle.cfg`. The defaults stay for the 0.4 mm nozzle; line
  widths, purge lengths and the first-layer test follow the setting.
- `BED_SOAK_ENABLE ENABLE=0|1`: the bed heat soak on or off for every
  print (saved; calibrations are kept).
- **Bed heat soak on the touch screen** (Settings > Bed Heat Soak): on/off,
  the calibrated times, and Calibrate with progress and Stop.
- After a nozzle change in Settings, the screen offers just the hotend PID
  tune and the first-layer Z offset test, not the whole setup
  (`SETUP_WIZARD_STEP STEP=pid HEATERS=extruder`).

### Fixed
- The speaker played nothing: the PWM driver refuses to switch off a
  channel that was never set up, which the player did before every note.

### Changed
- **Our 6.6 kernel always.** No more choice of kernel (`ad5x-kernel own`
  / `stock` are gone): Kiln OS runs our kernel on every printer, new
  installs included. The stock kernel stays in its boot slot only as the
  fallback when a start of ours fails, until an update brings another
  release of ours (`ad5x-kernel retry` tries again).

- Bed soak calibration holds the nozzle at its temperature for 5 minutes
  before heating the bed (`NOZZLE_SOAK=`), so the hotend still growing
  isn't counted as bed movement.
- Bed soak calibration copes with the load cells' scatter (about 0.03 mm):
  readings are averaged over 3 rounds and "settled" means within 0.02 mm,
  so it ends on its own instead of running 25 minutes; the saved time is
  the centre's (where the Z check probes), with the slowest corner's
  alongside.
- zMod's `START_PRINT` (zMod-sliced files) passes `SOAK=` on to
  `PRINT_START`; the soak applied to those files already.
- A cooler bed than the calibrated one never soaks longer than measured
  (a 55 °C PLA print after the 60 °C calibration: 420 s, not 565 s).
- A bed temperature without its own calibration uses the nearest one,
  scaled by how far the bed heats (an 80 C PETG print after a 60 C
  calibration soaks longer, not shorter); at most 10 minutes.

## v0.0.7

### Added
- **The speaker works:** short chimes when a print starts, finishes,
  fails or pauses and when the IFS auto-refills; `M300` beeps and zMod's
  `PLAY_MIDI FILE=` plays your own MIDI files (config folder `midi/`).
  On/off, volume and the sound per event on the touch screen (Settings >
  Sound > Printer sounds) or with `SOUND_SETUP`. HelixScreen's own sounds
  play on it too.
- **Time zone** as the first step of the setup wizard (also in "Run Setup
  Wizard"), for the screen's clock.
- **Plugins on the touch screen:** Settings > Plugins switches plugins on
  and off and installs, updates and removes the ones from the catalog
  (Notifications, Timelapse, Spoolman). No SSH, no reboot: Moonraker
  restarts by itself when needed. Console: `INSTALL_PLUGIN NAME=`,
  `UPDATE_PLUGIN`, `REMOVE_PLUGIN` (plugin API 1.4).

### Changed
- **Bed heat soak** before the Z check: the bed waits a little after
  reaching its temperature when it started cold, so the plate has stopped
  growing when Z is measured; the purge and brushing count. How long:
  measured on your printer with `BED_SOAK_CALIBRATE BED=80` (probes the
  centre and corners until they stop moving, saved per temperature), else
  3 s per degree the bed rose, at most 10 minutes. Optional "probe until
  stable" mode; `PRINT_START SOAK=` overrides; settings in the printer's
  `macros/print_start.cfg`.

## v0.0.6

### Added
- `git` on the printer, so plugins from their own repositories can be
  installed and then updated from Fluidd (docs/plugins.md).
- Plugin API 1.3: plugins can bring Python libraries and Moonraker
  components. Two new plugins use it:
  [kiln-notify](https://github.com/djvalic/kiln-notify) (notifications with
  a photo to Telegram, Discord, ntfy, e-mail and 100+ more) and
  [kiln-timelapse](https://github.com/djvalic/kiln-timelapse) (timelapse
  videos, with ffmpeg built for the printer).

### Changed
- The Spoolman plugin moved to its own repository,
  [kiln-spoolman](https://github.com/djvalic/kiln-spoolman), and updates
  from Fluidd on its own. It is no longer in the image.

### Fixed
- Installed updates no longer pile up on the data partition (each
  left an ~80 MB copy behind; 26 of them filled 2 GB). Only the latest is
  kept, and earlier ones are removed when the next update is staged.
- The recovery OS shows its release and real build date (it showed a
  fixed 2026-06-16).

## v0.0.5

### Added
- **Power-loss recovery.** While printing, the print's state is saved every
  10 s. After a power cut, `RESUME_INTERRUPTED CONFIRM=1` continues the
  print where it stopped (no Z homing into the part); `CLEAR_INTERRUPTED`
  forgets it.
- **IFS auto-refill** (off by default, `IFS_AUTO_REFILL ENABLE=1`): when a
  slot runs out mid-print, the printer switches to another slot with the
  same material and colour and carries on.
- **OrcaSlicer filament sync:** the IFS slots (material, colour,
  temperature) appear in Moonraker's `lane_data`, which OrcaSlicer's
  Moonraker printer agent reads. See docs/orcaslicer.md.
- **Spoolman plugin** (shipped, off): a Spoolman spool per IFS slot; the
  loaded slot's spool becomes the active one.
- **Recovery OS updates itself** together with the main OS.
- Releases publish their source code (GPL).

### Changed
- Starts about 20 s faster (11.6 s from start-up to ready, was 33 s).
- The clock starts at the last known time instead of 1970 until the
  network time is there.
- Smaller image (79 MB, was 92 MB): Python libraries as bytecode only.
- HelixScreen v1.1.0-beta.10.
- Klipper's `PID_CALIBRATE` now suggests about half the values it used
  to (an upstream fix). If temperatures oscillate, run the PID step again.
