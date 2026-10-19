# nopoop

zMod's purge modes for colour changes during a print. Slicer profiles for
zMod's nopoop / slicer-controlled purge set the mode in their start
G-code:

    SAVE_VARIABLE VARIABLE=use_trash_on_print VALUE=0

- `0`: the prime tower takes the purge ("nopoop").
- `2`: the slicer flushes at the purge box itself (`_GOTO_TRASH`,
  `G1 E...`, `_SBROS_TRASH`).
- `1` or not set: the printer purges at the box, as without this plugin.

With `0` or `2` a tool change still cuts, unloads and loads the new
filament, then fills the nozzle (`prime_length`, 12 mm, in `[ifs]`) at
the purge box and wipes, without purge rounds. Swaps outside a print
always purge. Tune `prime_length` in `local.cfg` (`[ifs]`): thin first
tower lines, raise it; blobs on the tower, lower it.

Enabled by default (nothing changes until a file sets the variable).
Mode numbers and idea: zMod, ninjamida's nopoop and QuickSwap.
