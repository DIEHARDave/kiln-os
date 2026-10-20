# Changelog

What changed for people using Kiln OS. Each release's notes (Gitea and
GitHub) take its section from here: `## vX.Y.Z`, or `## Unreleased` when
the release has no section of its own yet (rename it after the release).

## Unreleased

### Added
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
