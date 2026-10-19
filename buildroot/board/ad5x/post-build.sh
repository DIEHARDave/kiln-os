#!/bin/sh
# Runs after the target tree is assembled ($1 = target dir).
# - Vendor files (bundle-stock.sh): none by default (the printer's own
#   copies in /data/ad5x/vendor are used); a private build
#   (BR2_AD5X_BUNDLE_VENDOR=y or AD5X_VENDOR_FREE=0) copies the stock driver
#   modules and board tools from the local firmware download.
# - Drops Buildroot's S50nginx and sample pages: S63nginx starts nginx.
# - Makes Klipper's prebuilt c_helper.so newer than its sources, so klippy
#   doesn't try to rebuild it (the printer has no compiler).
# - Compiles Klipper and Moonraker to bytecode: the root is read-only, so
#   Python can't cache it and would compile everything at every start.
set -e
TARGET=$1

# Files of earlier builds that packages no longer install: Buildroot never
# removes anything from the target tree, so drop them here.
# S07ad5x-stock-helpers (replaced by S07ad5x-board) mounted slot A, now the
# recovery OS, and ran a second heartbeat.
for f in etc/init.d/S07ad5x-stock-helpers; do
	rm -f "$TARGET/$f"
done
REPO=$(cd "$BR2_EXTERNAL_AD5X_PATH/.." && pwd)

# Vendor files: none, or bundled in a private build (shared with the recovery image)
. "$BR2_EXTERNAL_AD5X_PATH/board/ad5x/bundle-stock.sh"
bundle_stock "$TARGET"

rm -f "$TARGET/etc/init.d/S50nginx" "$TARGET/etc/logrotate.d/nginx"
rm -rf "$TARGET/usr/html"

# Kiln OS version (docs/updates.md): AD5X_VERSION from tools/release.sh,
# else from git: v0.1.2+3.gabc1234 (3 commits after the tag v0.1.2;
# "+" is build metadata, so the printer offers v0.1.3 but not v0.1.2).
# The printer's update check (Moonraker's kiln_os) reads /etc/kiln-version.
KVER=${AD5X_VERSION:-}
KCOMMIT=$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)
if [ -z "$KVER" ]; then
	d=$(git -C "$REPO" describe --tags --long --match 'v[0-9]*' 2>/dev/null || true)
	if [ -n "$d" ]; then
		KVER=$(echo "$d" | sed 's/^\(.*\)-\([0-9]*\)-g\([0-9a-f]*\)$/\1+\2.g\3/')
	else
		KVER="v0.0.0+dev.g$(echo "$KCOMMIT" | cut -c1-7)"
	fi
fi
KDATE=$(date -u +%Y-%m-%d)
printf 'VERSION=%s\nCOMMIT=%s\nDATE=%s\n' "$KVER" "$KCOMMIT" "$KDATE" \
	> "$TARGET/etc/kiln-version"

# Marks our root filesystem (USB test mode looks for it)
echo "Kiln OS $KVER ($KDATE)" > "$TARGET/etc/ad5x-release"
# HelixScreen tells the AD5X from a K1 by this (or by stock's /usr/prog,
# which our root doesn't have), and then uses its factory touch fit.
echo 'VERSION_CODENAME="AD5X"' >> "$TARGET/usr/lib/os-release"
# The OS name Fluidd/Moonraker show (ID stays buildroot)
sed -i -e 's/^NAME=.*/NAME="Kiln OS"/' \
	-e "s/^PRETTY_NAME=.*/PRETTY_NAME=\"Kiln OS $KVER ($KDATE)\"/" \
	"$TARGET/usr/lib/os-release"
# Plugin API version (docs/plugin-api.md), from ad5x_plugins.py
api=$(sed -n 's/^PLUGIN_API_VERSION = "\(.*\)"$/\1/p' \
	"$TARGET/usr/lib/klipper/klippy/extras/ad5x_plugins.py")
if [ -n "$api" ]; then
	echo "AD5X_PLUGIN_API=\"$api\"" >> "$TARGET/usr/lib/os-release"
fi

CH=$TARGET/usr/lib/klipper/klippy/chelper
if [ -f "$CH/c_helper.so" ]; then
	touch -d '+1 day' "$CH/c_helper.so" 2>/dev/null || touch "$CH/c_helper.so"
fi

# Same Python version on the host (host-python3) as on the target.
# unchecked-hash: the .pyc stays valid whatever the file times are.
for d in usr/lib/klipper usr/lib/moonraker; do
	[ -d "$TARGET/$d" ] || continue
	"$HOST_DIR/bin/python3" -m compileall -q -j 0 \
		--invalidation-mode unchecked-hash "$TARGET/$d" >/dev/null
done
