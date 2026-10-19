#!/usr/bin/env python3
"""Start the AD5X toolhead board (eboard) application from its bootloader.

After power-on the eboard bootloader prints "Ready" at 115200 baud and waits.
Sending 'A' makes it answer 0x06 (ACK) and jump to the application (Klipper),
which then talks at 230400. Run this once before klippy starts.

usage: boot_eboard.py [--port /dev/ttyS5] [--baud 115200] [--tries 20] [--listen]

Exit codes: 0 app started, 1 no ACK, 2 nothing heard from the board (already
running the app, or not powered), 3 port error. With --listen it only checks
that the bootloader is waiting ("Ready") and sends nothing: 0 waiting, 2 not
(ad5x-mcu flashes the board while it waits).

Written from the behaviour described in docs/motion-mcu.md; no vendor code.
"""
import argparse
import os
import sys
import termios
import time
import tty

BAUDS = {9600: termios.B9600, 57600: termios.B57600,
         115200: termios.B115200, 230400: termios.B230400}
ACK = b"\x06"

def open_port(port, baud):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY)
    tty.setraw(fd)
    attrs = termios.tcgetattr(fd)
    attrs[4] = attrs[5] = BAUDS[baud]
    attrs[2] |= termios.CLOCAL | termios.CREAD
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 1          # reads return after 0.1 s
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIFLUSH)
    return fd

def boot(fd, tries, log, listen=False):
    heard = False
    for _ in range(tries):
        data = os.read(fd, 64)
        if not data:
            continue
        heard = True
        log("recv %r" % (data,))
        if b"Ready" in data:
            if listen:
                return 0
            break
    if not heard or listen:
        return 2
    for _ in range(tries):
        os.write(fd, b"A")
        reply = os.read(fd, 1)
        log("sent 'A', recv %r" % (reply,))
        if reply == ACK:
            return 0
    return 1

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", default="/dev/ttyS5")
    ap.add_argument("--baud", type=int, default=115200, choices=sorted(BAUDS))
    ap.add_argument("--tries", type=int, default=20)
    ap.add_argument("--listen", action="store_true",
                    help="only check that the bootloader waits; send nothing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    log = (lambda m: print("boot_eboard: " + m, file=sys.stderr)) \
        if args.verbose else (lambda m: None)
    try:
        fd = open_port(args.port, args.baud)
    except OSError as e:
        print("boot_eboard: %s: %s" % (args.port, e), file=sys.stderr)
        return 3
    try:
        rc = boot(fd, args.tries, log, args.listen)
    finally:
        os.close(fd)
    if args.listen:
        print("boot_eboard: " + ("bootloader waiting" if rc == 0 else
              "no bootloader (application running, or no power)"), file=sys.stderr)
        return rc
    msg = {0: "eboard application started",
           1: "no ACK from the eboard bootloader",
           2: "nothing heard from the eboard (already running, or no power)"}
    print("boot_eboard: " + msg[rc], file=sys.stderr)
    return rc

if __name__ == "__main__":
    sys.exit(main())
