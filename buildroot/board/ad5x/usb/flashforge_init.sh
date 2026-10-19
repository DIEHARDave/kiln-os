#!/bin/sh
# Kiln OS, USB test mode. Goes on the FAT partition of the test stick.
#
# Stock /usr/prog/app_startup.sh runs /mnt/flashforge_init.sh from a FAT
# USB stick at boot, as root, before the Flashforge app and zMod start.
# This script starts our system from the stick's ext4 partition (chroot on
# the running stock kernel) and never returns, so the stock app never runs.
# Unplug the stick and power-cycle: stock (and zMod) boot as before.
# Nothing on the printer's own storage is changed, except our files under
# /usr/data/ad5x (Klipper config, logs).
#
# Never put an AD5X-*.tgz on this stick: stock would install it as a
# firmware update.

LOG=/mnt/ad5x-usb.log
exec >>$LOG 2>&1
echo "=== $(date) AD5X USB test mode, args: $*"

ROOT=/tmp/ad5x-root
mkdir -p $ROOT

# 1. Our root filesystem: the first USB ext4 partition with /etc/ad5x-release
found=
for p in /dev/sd[a-z][1-4]; do
	[ -b "$p" ] || continue
	mount -t ext4 -o ro,noatime "$p" $ROOT 2>/dev/null || continue
	if [ -f $ROOT/etc/ad5x-release ]; then found=$p; break; fi
	umount $ROOT
done
if [ -z "$found" ]; then
	echo "no ext4 partition with etc/ad5x-release; booting stock"
	exit 1    # non-zero: stock carries on with its normal start-up
fi
echo "root: $found ($(cat $ROOT/etc/ad5x-release))"

# 2. What stock app_startup.sh does after this point and we still need:
#    /usr/prog/etc over /etc (root password and SSH host key for stock's
#    dropbear, which is already running), the board heartbeat (PC11
#    toggle), Ethernet MAC from /usr/prog/MAC, the Wi-Fi and touch drivers.
grep -q ' /etc ' /proc/mounts || mount --bind /usr/prog/etc /etc
/usr/prog/sys_start.sh &
if [ -f /usr/prog/MAC ]; then
	ifconfig eth0 down
	ifconfig eth0 hw ether "$(cat /usr/prog/MAC)"
	ifconfig eth0 up
	[ -f /var/run/udhcpc.pid ] && kill "$(cat /var/run/udhcpc.pid)"
	# Stock's own lease script, plus the DNS servers for our system: stock
	# also runs dhcpcd, which leaves its resolv.conf without nameservers.
	cat > /tmp/ad5x-dhcp.sh <<'EOF2'
#!/bin/sh
/usr/share/udhcpc/default.script "$@"
case "$1" in
bound|renew)
	: > /tmp/ad5x-resolv.conf
	for d in $dns; do echo "nameserver $d" >> /tmp/ad5x-resolv.conf; done
	cp /tmp/ad5x-resolv.conf /tmp/ad5x-root/run/resolv.conf 2>/dev/null
	;;
esac
EOF2
	chmod 755 /tmp/ad5x-dhcp.sh
	/sbin/udhcpc -b -i eth0 -p /var/run/udhcpc.pid -s /tmp/ad5x-dhcp.sh
fi
grep -q '^8821cu ' /proc/modules || insmod /usr/prog/modules/8821cu.ko power_on=PB07
grep -q '^tsc2007_touch ' /proc/modules || insmod /module_driver/tsc2007_touch.ko \
	tsc_irq_gpio=PC07 tsc_power_on_gpio=-1 tsc_regulator_name=-1 tsc_i2c_bus=0 \
	tsc_i2c_addr=0x48 tsc_x_plate_ohms=660 tsc_max_rt=600 tsc_fuzzx=0 \
	tsc_fuzzy=0 tsc_fuzzz=0 tsc_poll_period=0 tsc_x_coords_max=800 \
	tsc_y_coords_max=480 tsc_xy_coords_exchange=0 tsc_x_coords_flip=0 \
	tsc_y_coords_flip=1 tsc_x_actrue_min=0 tsc_x_actrue_max=4096 \
	tsc_y_actrue_min=0 tsc_y_actrue_max=4096

# 3. The mounts BusyBox init would make, then the printer's data partition
#    (already mounted by stock at /usr/data) at /data.
mount --bind /dev $ROOT/dev
mount -t devpts devpts $ROOT/dev/pts 2>/dev/null
mount -t proc proc $ROOT/proc
mount -t sysfs sysfs $ROOT/sys
mount -t tmpfs -o mode=1777 tmpfs $ROOT/tmp
mount -t tmpfs -o mode=0755,nosuid,nodev tmpfs $ROOT/run
mkdir -p $ROOT/dev/shm 2>/dev/null
mount --bind /usr/data $ROOT/data
# DNS (our /etc/resolv.conf points to /run/resolv.conf): from the lease,
# else the default gateway. The lease script keeps it current.
if [ -s /tmp/ad5x-resolv.conf ]; then
	cp /tmp/ad5x-resolv.conf $ROOT/run/resolv.conf
else
	gw=$(ip route | awk '/^default/ {print $3; exit}')
	[ -n "$gw" ] && echo "nameserver $gw" > $ROOT/run/resolv.conf
fi
# Stock's settings (usershare, mounted by stock at /usr/prog), read-only,
# for the per-printer calibration (S05ad5x-data). Mounting the partition
# a second time fails while stock has it mounted.
mkdir -p $ROOT/tmp/usershare
mount --bind /usr/prog $ROOT/tmp/usershare
mount -o remount,bind,ro $ROOT/tmp/usershare

# 4. Our start-up scripts. Stock's dropbear keeps running (root/root over
#    SSH, the way back in); ours finds port 22 taken and stays off.
#    Get a shell in our system with: chroot /tmp/ad5x-root /bin/sh
echo "starting our init scripts"
AD5X_USB=1 chroot $ROOT /etc/init.d/rcS
echo "running; stock start-up is held here"

# Never return: stock would otherwise go on to start its own app.
while true; do sleep 3600; done
