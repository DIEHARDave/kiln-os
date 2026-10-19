# Kiln OS: A/B slot helpers (sourced). The boot loader picks the slot
# from the ota partition: "ota:kernel2" boots kernel2 + rootfs2 (slot B),
# anything else kernel + rootfs (slot A). See docs/boot-slots.md.
#
# Sets SLOT/OTHER (A or B, empty when not booted as an installed system,
# e.g. in USB test mode) and provides part, flag_for, set_flag.

part() {	# GPT name -> /dev path
	for u in /sys/class/block/*/uevent; do
		grep -qx "PARTNAME=$1" "$u" && { echo /dev/$(sed -n 's/^DEVNAME=//p' "$u"); return 0; }
	done
	return 1
}
flag_for() { [ "$1" = B ] && echo ota:kernel2 || echo ota:kernel; }
rootfs_of() { [ "$1" = B ] && part rootfs2 || part rootfs; }
kernel_of() { [ "$1" = B ] && part kernel2 || part kernel; }
set_flag() {	# slot
	echo "$(flag_for $1)" > "$(part ota)" && sync
}
read_flag() { head -c 11 "$(part ota)" | tr -d '\0\n'; }

SLOT= OTHER=
# ad5x.noslot: a test boot of another kernel (kernel-ingenic66/chainload)
# that must not touch the boot flag.
if [ -z "$AD5X_USB" ] && [ -f /etc/ad5x-release ] &&
   ! grep -qw ad5x.noslot /proc/cmdline; then
	case "$(sed -n 's/.*root=\([^ ]*\).*/\1/p' /proc/cmdline)" in
	"$(part rootfs)"|PARTLABEL=rootfs) SLOT=A OTHER=B ;;
	"$(part rootfs2)"|PARTLABEL=rootfs2) SLOT=B OTHER=A ;;
	esac
fi
