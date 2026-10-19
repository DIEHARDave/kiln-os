# MCU data dictionaries

The data dictionaries (`klipper.dict`) of the Klipper firmware flashed on
the printer's mainboard and eboard (`tools/build_mcu.sh`, mainline Klipper
plus `klipper/mcu-patches`). `FLASHED` names the version on the boards.

Klipper's host checks every command it sends against these. A host update
that needs something the boards' firmware doesn't have would stop with
"MCU Protocol error", so `tools/test_image.sh` runs the image's Klipper in
test mode against them, and the update builder (`docs/updates.md`) only
releases a newer Klipper when that run passes. After reflashing the boards
with a newer build, add its dictionaries here and update `FLASHED`.
