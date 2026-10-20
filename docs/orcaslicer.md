# OrcaSlicer with Kiln OS

## Uploading and printing

Add the printer in OrcaSlicer as a physical printer with host type
**Octo/Klipper** and the printer's address (e.g. `192.168.1.56`). Moonraker
answers on port 80 through nginx (and on 7125).

## The IFS slots in OrcaSlicer (filament sync)

Kiln OS keeps the IFS slots in Moonraker's database, namespace `lane_data`,
in the format the AFC filament changer uses (Moonraker component
`kiln_lanes`, `moonraker/components/kiln_lanes.py`):

| Record | Fields |
|---|---|
| `lane1` .. `lane4` (IFS slot 1-4) | `lane`: slicer tool `"0"`..`"3"` (slot 1 = T0); `material` (`""` when the slot has no filament or no type); `color` (`#RRGGBB`); `nozzle_temp`; `bed_temp` (0); `name`, `vendor`, `spool_id`, `scan_time` (empty) |

It's updated whenever a slot's material, colour or temperature changes
(touch screen, `IFS_SET_MATERIAL`) or a spool goes in or out.

OrcaSlicer's **Moonraker printer agent** reads it and fills its filament
list with what is loaded. In OrcaSlicer builds that have it (nightlies after
2.4.2): Preferences > Developer > Experimental Features > "Use printer
agents instead of print hosts", then pick the printer in the Device tab and
sync the filaments. Without that option OrcaSlicer uploads as before and
ignores `lane_data`.

Read it by hand:

    curl http://192.168.1.56/server/database/item?namespace=lane_data

## Tools and slots

A slicer tool T0-T3 loads IFS slot 1-4 unless the file maps it otherwise
with `IFS_MAP_TOOL TOOL=n SLOT=m` (per print). The separate OrcaSlicer
plugin [kiln-orca](https://github.com/djvalic/kiln-orca) adds those lines to exported
G-code by matching each tool's material and colour against the slots.
