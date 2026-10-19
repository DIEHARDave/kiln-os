#!/bin/sh
# Print the sw-description for an AD5X main-OS update (shared by
# tools/make_swu.sh on the laptop and ad5x-zip-to-swu on the recovery OS).
#
# usage: mk-sw-description.sh VERSION ROOTFS SCRIPT [KERNEL]
#   ROOTFS  rootfs.squashfs, SCRIPT ad5x-slot-b.sh, KERNEL kernel.uimage
# Every artifact gets its sha256; the script's data carries the sizes and
# sha256s it verifies after writing (docs/recovery-os.md).
set -e
VERSION=$1 ROOTFS=$2 SCRIPT=$3 KERNEL=$4
sha() { sha256sum "$1" | cut -d' ' -f1; }
size() { wc -c < "$1" | tr -d ' '; }
RSIZE=$(size "$ROOTFS") RSHA=$(sha "$ROOTFS") SSHA=$(sha "$SCRIPT")
DATA="rootfs_size=$RSIZE rootfs_sha256=$RSHA"
KIMG=
if [ -n "$KERNEL" ]; then
	KSIZE=$(size "$KERNEL") KSHA=$(sha "$KERNEL")
	DATA="$DATA kernel_size=$KSIZE kernel_sha256=$KSHA"
	KIMG="		{
			filename = \"kernel.uimage\";
			device = \"/dev/disk/by-partlabel/kernel2\";
			type = \"raw\";
			sha256 = \"$KSHA\";
		},"
fi
cat <<DESC
software =
{
	version = "$VERSION";
	description = "Kiln OS (main system) for slot B";
	hardware-compatibility: [ "1.0" ];

	images: (
$KIMG
		{
			filename = "rootfs.squashfs";
			device = "/dev/disk/by-partlabel/rootfs2";
			type = "raw";
			sha256 = "$RSHA";
		}
	);

	scripts: (
		{
			filename = "ad5x-slot-b.sh";
			type = "shellscript";
			data = "$DATA";
			sha256 = "$SSHA";
		}
	);
}
DESC
