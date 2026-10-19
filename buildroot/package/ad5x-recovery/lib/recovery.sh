# AD5X recovery OS: shared shell helpers (sourced by the init scripts and
# the ad5x-* tools). See docs/recovery-os.md.
#
# Partitions are found by their GPT name (PARTNAME in sysfs), as in the
# main OS (/usr/lib/ad5x/slot.sh). For tests on the laptop every system
# path can be redirected (tools/test_recovery.sh):
#   AD5X_SYS      sysfs root            (default /sys)
#   AD5X_DEV      device directory      (default /dev)
#   AD5X_CMDLINE  kernel command line   (default /proc/cmdline)
#   AD5X_MOUNTS   mount table           (default /proc/mounts)
#   AD5X_DATA     userdata mount point  (default /data)
#   AD5X_RUN      runtime state dir     (default /run/ad5x)

: "${AD5X_SYS:=/sys}" "${AD5X_DEV:=/dev}" "${AD5X_CMDLINE:=/proc/cmdline}"
: "${AD5X_MOUNTS:=/proc/mounts}" "${AD5X_DATA:=/data}" "${AD5X_RUN:=/run/ad5x}"

# Partition table compiled into the SPL (docs/boot-slots.md): name, start
# LBA, sectors. The SPL boots by these numbers, not by the GPT; anything that
# writes a slot checks the GPT still agrees.
RC_SPL_TABLE="kernel:2048:16384 rootfs:18432:204800 kernel2:223232:16384
rootfs2:239616:204800 ota:444416:2048 usershare:446464:2097152
userdata:2543616:12238848"

# Names the backup/restore tools know, in disk order. "boot" is the first
# MiB of the disk (protective MBR + Ingenic boot block, GPT, SPL, U-Boot).
RC_PARTS="kernel rootfs kernel2 rootfs2 ota usershare userdata"

rc_say() { echo "${0##*/}: $*"; }
rc_die() { echo "${0##*/}: error: $*" >&2; exit 1; }

# sysfs directory of a partition, by GPT name
rc_part_sys() {
	for u in "$AD5X_SYS"/class/block/*/uevent; do
		[ -f "$u" ] || continue
		grep -qx "PARTNAME=$1" "$u" 2>/dev/null && { echo "${u%/uevent}"; return 0; }
	done
	return 1
}
# GPT name -> device path
rc_part() {
	s=$(rc_part_sys "$1") || return 1
	echo "$AD5X_DEV/$(sed -n 's/^DEVNAME=//p' "$s/uevent")"
}
rc_part_bytes() { s=$(rc_part_sys "$1") && echo $(( $(cat "$s/size") * 512 )); }
rc_part_start() { s=$(rc_part_sys "$1") && cat "$s/start"; }
# The disk holding the slots (mmcblk0): parent of the "rootfs" partition
rc_disk() {
	s=$(rc_part_sys rootfs) || return 1
	d=$(readlink -f "$s/..") || return 1
	echo "$AD5X_DEV/${d##*/}"
}
# Size of a name: a partition, or "boot" = the first MiB of the disk
rc_bytes() { [ "$1" = boot ] && echo 1048576 || rc_part_bytes "$1"; }
rc_dev() { [ "$1" = boot ] && rc_disk || rc_part "$1"; }

# GPT entry agrees with the SPL's built-in table?
rc_spl_ok() {
	want=$(echo "$RC_SPL_TABLE" | tr ' ' '\n' | grep "^$1:") || return 1
	s=$(rc_part_sys "$1") || return 1
	[ "$(cat "$s/start")" = "$(echo "$want" | cut -d: -f2)" ] &&
	[ "$(cat "$s/size")" = "$(echo "$want" | cut -d: -f3)" ]
}

rc_root() { sed -n 's/.*root=\([^ ]*\).*/\1/p' "$AD5X_CMDLINE"; }
# Running slot from root=: A (rootfs, p2) or B (rootfs2, p4), else empty
rc_slot() {
	r=$(rc_root); r=${r##*/}
	case "$r" in
	"$(basename "$(rc_part rootfs 2>/dev/null)" 2>/dev/null)") echo A ;;
	"$(basename "$(rc_part rootfs2 2>/dev/null)" 2>/dev/null)") echo B ;;
	esac
}
rc_mounted() { grep -q "^$1 " "$AD5X_MOUNTS"; }
rc_mountpoint_of() { awk -v d="$1" '$1 == d { print $2; exit }' "$AD5X_MOUNTS"; }

# Boot flag (first sector of "ota"): the SPL boots slot B on "ota:kernel2"
rc_read_flag() { head -c 11 "$(rc_part ota)" 2>/dev/null | tr -d '\0\n'; }
rc_flag_slot() { [ "$(rc_read_flag)" = ota:kernel2 ] && echo B || echo A; }
rc_set_flag() {	# A|B, written as stock does (echo, then sync)
	o=$(rc_part ota) || return 1
	rc_spl_ok ota || { echo "ota partition doesn't match the SPL table" >&2; return 1; }
	if [ "$1" = B ]; then echo ota:kernel2 > "$o"; else echo ota:kernel > "$o"; fi
	sync
	[ "$(rc_flag_slot)" = "$1" ]
}

rc_drop_caches() { sync; { echo 3 > /proc/sys/vm/drop_caches; } 2>/dev/null; true; }
# sha256 of the first SIZE bytes of a file or device
rc_sha() { head -c "$2" "$1" | sha256sum | cut -d' ' -f1; }
rc_fsize() { wc -c < "$1" | tr -d ' '; }

# What a rootfs partition holds: "ad5x <release>", "recovery <release>",
# "stock", "empty" (no squashfs) or "unknown" (squashfs, not mountable here)
rc_slot_holds() {
	dev=$(rc_part "$1") || { echo unknown; return; }
	[ "$(head -c 4 "$dev" 2>/dev/null)" = hsqs ] || { echo empty; return; }
	m=$AD5X_RUN/inspect.$$
	mkdir -p "$m"
	if ! mount -t squashfs -o ro "$dev" "$m" 2>/dev/null; then
		rmdir "$m"; echo unknown; return
	fi
	if [ -f "$m/etc/ad5x-recovery" ]; then echo "recovery $(cat "$m/etc/ad5x-release" 2>/dev/null)"
	elif [ -f "$m/etc/ad5x-release" ]; then echo "ad5x $(cat "$m/etc/ad5x-release")"
	elif [ -d "$m/usr/prog" ] || [ -f "$m/etc/ota_bin/ota_local_method.sh" ]; then echo stock
	else echo unknown
	fi
	umount "$m"; rmdir "$m"
}

# Bytes used by a squashfs (superblock bytes_used, offset 40, 8 bytes LE)
rc_squashfs_used() { od -An -t u8 -j 40 -N 8 "$1" | tr -d ' '; }
# uImage (legacy) total length: 64-byte header + ih_size (big endian, at 12)
rc_uimage_len() {
	[ "$(od -An -t x1 -N 4 "$1" | tr -d ' \n')" = 27051956 ] || return 1
	echo $(( 0x$(od -An -t x1 -j 12 -N 4 "$1" | tr -d ' \n') + 64 ))
}

# USB sticks: mounted at /run/ad5x/usb/<dev> by ad5x-usb mount
RC_USB=$AD5X_RUN/usb
rc_usb_mounts() {
	awk -v p="$RC_USB/" 'index($2, p) == 1 { print $2 }' "$AD5X_MOUNTS"
}
