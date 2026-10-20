# Changelog

What changed for people using Kiln OS. Each release's notes (Gitea and
GitHub) take its section from here: `## vX.Y.Z`, or `## Unreleased` when
the release has no section of its own yet (rename it after the release).

## Unreleased

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
