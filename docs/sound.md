# Sound

The AD5X has a small piezo speaker on pin PC12, driven by PWM channel 13
(the stock UI plays its tone tables there; it never uses the audio codec).
Kiln OS plays chimes on print events, `M300` beeps and MIDI files on it,
and HelixScreen plays its own UI sounds on the same channel.

## What it can do

A piezo on a PWM pin makes a square wave at one pitch at a time, so a
"song" is a list of notes: a MIDI file. `ad5x-sound` plays one note at a
time, the highest of those sounding together (usually the melody), and
skips drum tracks. Real audio (WAV) is not possible on this hardware.
Volume is the duty cycle (100 = 50 % duty, the loudest a square wave gets);
lower values are quieter, unevenly. Stock has on/off only.

## Using it

From the touch screen: **Settings > Sound > Printer Sounds**: on/off,
volume, and for each event the sound it plays (or Off), with a play
button to hear it.

From the console (Fluidd, HelixScreen, macros, slicer G-code):

```
M300 S1000 P200                  beep: S Hz, P milliseconds
PLAY_MIDI FILE=complete.mid      a MIDI file (zMod's command name)
PLAY_SOUND EVENT=complete        what an event plays
SOUND_STOP
SOUND_SETUP                      settings and the sound files
SOUND_SETUP ENABLE=0             all printer sounds off
SOUND_SETUP VOLUME=40
SOUND_SETUP COMPLETE=mytune.mid PAUSED=0
```

Events: `startup` (Klipper ready; off by default), `start` (print
started), `complete`, `error` (failed, or Klipper shut down),
`cancelled` (off by default), `paused` (filament runout, IFS problem,
`PAUSE`), `refill` (IFS auto-refill switched slots).

Settings are kept in the save variable `ad5x_sound`;
`printer.ad5x_sound` shows `speaker`, `enabled`, `volume`, `events`,
`files`, `playing`.

## Your own sounds

Put `.mid` files in the config folder's `midi/` (Fluidd: Configuration,
create the folder `midi`, upload), then pick them on the screen or with
`SOUND_SETUP <EVENT>=<file>` / `PLAY_MIDI FILE=<file>`. A file of yours
with the name of a shipped one replaces it. MIDI files found online vary
a lot: one with the melody on its own track (often piano) works best.
Playback stops after 10 minutes.

The shipped sounds (`start`, `complete`, `error`, `paused`, `refill`,
`startup`, `beep`) are short chimes of our own, written by
`tools/make_sounds.py` into `klipper/sounds/` (installed in
`/usr/share/ad5x/sounds`).

## How it fits together

| Part | What |
|---|---|
| `kernel-ingenic66/ad5x.dts` | `&pwm` with `pinctrl-0 = <&pwm13_pc>`: PC12 muxed to PWM 13 (the driver doesn't mux pins itself) |
| `S35ad5x-sound` | Exports `pwmchip0/pwm13`, lets user `klipper` drive it, writes `/run/ad5x-sound.conf` (`PWM=pwmchip0/pwm13`); no file means no speaker (e.g. on the stock kernel) |
| `/usr/bin/ad5x-sound` | The player: `tone FREQ MS`, `play FILE.mid`, `notes FILE.mid` (prints the notes), `stop`; one at a time |
| `klipper/extras/ad5x_sound.py` (`[ad5x_sound]`) | `M300`, `PLAY_MIDI`, `PLAY_SOUND`, `SOUND_STOP`, `SOUND_SETUP`, event sounds (watches `print_stats` and `ifs.refill`) |
| HelixScreen patch `0007` | Its sysfs PWM sound backend on our build (`HELIX_PWM_SOUND=0:13` from `S70helixscreen`), and the Printer Sounds card |

Never write the channel's `polarity`: this kernel driver applies it to
channel 0. HelixScreen and `ad5x-sound` share the channel, so a tap during
a chime cuts into it.

zMod compatibility: `M300` and `PLAY_MIDI FILE=` work as in zMod; zMod's
`MIDI_START`/`MIDI_END` settings map to `SOUND_SETUP START=`/`COMPLETE=`.
