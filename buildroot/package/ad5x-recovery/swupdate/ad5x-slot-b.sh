#!/bin/sh
# Shell script inside every main-OS .swu (tools/make_swu.sh), run by
# SWUpdate on the recovery OS (slot A):
#   ad5x-slot-b.sh preinst|postinst|postfailure [key=value...]
# The key=values come from the signed sw-description ("data"):
#   rootfs_size= rootfs_sha256= [kernel_size= kernel_sha256=]
#
# preinst      we run from slot A (rootfs, p2); rootfs2/kernel2/ota match
#              the SPL's partition table; rootfs2 isn't mounted; an update
#              without a kernel (the normal case: releases carry none) needs
#              a uImage already in kernel2 (the printer's own stock kernel),
#              which it keeps; the boot flag is pointed at slot A (here)
#              while slot B is rewritten.
# postinst     read back rootfs2 (and kernel2) and compare with the
#              sha256s; mount rootfs2 read-only and require
#              /etc/ad5x-release and /linuxrc; then boot flag -> slot B.
# postfailure  boot flag stays on slot A.
# Any failure: exit 1, SWUpdate reports the update as failed.
. /usr/lib/ad5x-recovery/recovery.sh || exit 1
phase=$1; shift
for kv in "$@"; do
	case "$kv" in
	rootfs_size=*|rootfs_sha256=*|kernel_size=*|kernel_sha256=*) eval "${kv%%=*}=\${kv#*=}" ;;
	esac
done
say() { echo "ad5x-slot-b $phase: $*"; }
fail() { echo "ad5x-slot-b $phase: FAILED: $*" >&2; ad5x-bootlog "swu $phase failed: $*" 2>/dev/null; exit 1; }

case "$phase" in
preinst)
	[ "$(rc_slot)" = A ] || fail "not running from slot A (root $(rc_root))"
	for n in rootfs2 kernel2 ota; do
		rc_spl_ok $n || fail "GPT entry $n differs from the SPL table"
		[ "$(readlink -f "$AD5X_DEV/disk/by-partlabel/$n")" = "$(readlink -f "$(rc_part $n)")" ] ||
			fail "$AD5X_DEV/disk/by-partlabel/$n doesn't point at $(rc_part $n)"
	done
	rc_mounted "$(rc_part rootfs2)" && fail "rootfs2 is mounted"
	[ -n "$rootfs_size" ] && [ -n "$rootfs_sha256" ] || fail "no rootfs size/sha256 in sw-description"
	[ "$rootfs_size" -le "$(rc_part_bytes rootfs2)" ] || fail "rootfs $rootfs_size bytes doesn't fit rootfs2"
	if [ -z "$kernel_size" ]; then
		# rootfs-only update: slot B keeps the kernel it has. Without one
		# there, it gets the kernel this recovery runs on (kernel, p1: the
		# printer's own stock kernel), never one from the update.
		if ! rc_uimage_len "$(rc_part kernel2)" >/dev/null; then
			alen=$(rc_uimage_len "$(rc_part kernel)") ||
				fail "neither kernel2 nor kernel holds a kernel (uImage), and the update brings none"
			say "kernel2 holds no kernel: copying this slot's kernel ($alen bytes)"
			mkdir -p "$AD5X_RUN"
			head -c "$alen" "$(rc_part kernel)" > "$AD5X_RUN/kernel.copy" &&
				dd if="$AD5X_RUN/kernel.copy" of="$(rc_part kernel2)" bs=65536 conv=notrunc 2>/dev/null ||
				fail "copying the kernel to kernel2"
			rc_drop_caches
			[ "$(rc_sha "$(rc_part kernel2)" "$alen")" = "$(rc_sha "$AD5X_RUN/kernel.copy" "$alen")" ] ||
				fail "kernel2 copy reads back wrong"
			rm -f "$AD5X_RUN/kernel.copy"
		fi
		klen=$(rc_uimage_len "$(rc_part kernel2)") || fail "kernel2 holds no kernel (uImage)"
		[ "$klen" -le "$(rc_part_bytes kernel2)" ] || fail "kernel2 uImage header says $klen bytes, more than the partition"
		say "keeping the kernel in kernel2 ($klen bytes)"
	fi
	if [ "$(rc_flag_slot)" != A ]; then
		rc_set_flag A || fail "can't point the boot flag at slot A"
	fi
	say "writing slot B; boot flag $(rc_read_flag)"
	ad5x-bootlog "swu preinst ok" 2>/dev/null
	;;
postinst)
	rc_drop_caches
	got=$(rc_sha "$(rc_part rootfs2)" "$rootfs_size")
	[ "$got" = "$rootfs_sha256" ] || fail "rootfs2 reads back $got, expected $rootfs_sha256"
	if [ -n "$kernel_size" ]; then
		got=$(rc_sha "$(rc_part kernel2)" "$kernel_size")
		[ "$got" = "$kernel_sha256" ] || fail "kernel2 reads back $got, expected $kernel_sha256"
		rc_uimage_len "$(rc_part kernel2)" >/dev/null || fail "kernel2 holds no uImage"
	else
		rc_uimage_len "$(rc_part kernel2)" >/dev/null || fail "kernel2 holds no uImage"
	fi
	m=$AD5X_RUN/swu-check
	mkdir -p "$m"
	mount -t squashfs -o ro "$(rc_part rootfs2)" "$m" || fail "rootfs2 doesn't mount as squashfs"
	ok=; [ -f "$m/etc/ad5x-release" ] && { [ -e "$m/linuxrc" ] || [ -L "$m/linuxrc" ]; } && ok=1
	rel=$(cat "$m/etc/ad5x-release" 2>/dev/null)
	umount "$m"
	[ -n "$ok" ] || fail "rootfs2 lacks /etc/ad5x-release or /linuxrc"
	rc_set_flag B || fail "can't point the boot flag at slot B"
	say "slot B verified ($rel); boot flag $(rc_read_flag)"
	ad5x-bootlog "swu postinst ok: $rel" 2>/dev/null
	;;
postfailure)
	[ "$(rc_flag_slot)" = A ] || rc_set_flag A
	say "update failed; boot flag $(rc_read_flag)"
	;;
esac
exit 0
