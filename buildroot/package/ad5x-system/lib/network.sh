# Kiln OS: bring up a network interface from /data/ad5x/network.conf
# (shared by the main OS and the recovery OS). Sourced; call net_up IFACE.
#
#   MODE=dhcp|static        dhcp when the file or MODE is missing
#   ADDRESS=192.168.1.50/24 static: address with prefix length
#   GATEWAY=192.168.1.1     static: default route (optional)
#   DNS="192.168.1.1 1.1.1.1"  static: name servers (optional)
#   IFACE=eth0              optional, overrides the interface name
#
# An invalid static setup falls back to DHCP.

net_valid_cidr() {
	echo "$1" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}/([0-9]|[12][0-9]|3[0-2])$'
}

net_up() {
	iface=${1:-eth0}
	MODE=dhcp ADDRESS= GATEWAY= DNS= IFACE=
	[ -f /data/ad5x/network.conf ] && . /data/ad5x/network.conf
	[ -n "$IFACE" ] && iface=$IFACE
	ip link set "$iface" up 2>/dev/null || ifconfig "$iface" up
	if [ "$MODE" = static ]; then
		if net_valid_cidr "$ADDRESS" && ip addr flush dev "$iface" && \
		   ip addr add "$ADDRESS" dev "$iface"; then
			[ -n "$GATEWAY" ] && ip route replace default via "$GATEWAY" dev "$iface"
			if [ -n "$DNS" ]; then
				: > /run/resolv.conf
				for d in $DNS; do echo "nameserver $d" >> /run/resolv.conf; done
			fi
			echo "network: $iface static $ADDRESS${GATEWAY:+ via $GATEWAY}"
			return 0
		fi
		echo "network: invalid static setup in /data/ad5x/network.conf (ADDRESS='$ADDRESS'), using DHCP"
	fi
	udhcpc -b -i "$iface" -p /var/run/udhcpc.$iface.pid >/dev/null
	echo "network: $iface DHCP"
}
