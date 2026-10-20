# spoolman

[Spoolman](https://github.com/Donkie/Spoolman) keeps a list of your spools
and how much filament is left on each. Moonraker has the Spoolman client
built in; the Spoolman server runs on another machine (a NAS, a Raspberry
Pi, Docker). This plugin books each IFS slot's filament to its own spool.

## Connect Moonraker to Spoolman

Add to the printer's `moonraker.conf` (Fluidd: Configuration):

    [spoolman]
    server: http://192.168.1.10:7912
    sync_rate: 5

After a Moonraker restart Fluidd shows a Spoolman panel, and the filament
a print uses is booked to the *active* spool. That much works without this
plugin, with one active spool chosen by hand.

## One spool per IFS slot (this plugin)

    ENABLE_PLUGIN NAME=spoolman

Then give each slot the ID of the spool loaded in it:

    SPOOLMAN_SET_SLOT SLOT=1 SPOOL=12
    SPOOLMAN_SET_SLOT SLOT=2 SPOOL=7
    SPOOLMAN_SET_SLOT SLOT=2 SPOOL=        (clears it)
    SPOOLMAN_SLOTS                          (lists them)

From then on every load or swap (T0-T3, IFS_LOAD, auto-refill) makes the
loaded slot's spool the active one, so a multicolour print books each
colour to its own spool; emptying the nozzle clears the active spool. While
no slot has a spool the active spool is left alone. The IDs are kept in
`variables.cfg` (`spoolman_slots`); `printer.spoolman_slots.slots` shows
them.

How it hooks in: Kiln OS sends the Klipper event `ifs:loaded` (plugin API
1.2) whenever the slot in the nozzle changes; the plugin calls Moonraker's
`spoolman_set_active_spool` then.
