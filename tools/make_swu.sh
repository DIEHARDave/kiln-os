#!/bin/bash
# Build an SWUpdate image (.swu) of the MAIN OS for the recovery OS,
# which installs it into slot B (docs/recovery-os.md).
#
# usage: tools/make_swu.sh [-r ROOTFS] [-k KERNEL] [-V VERSION] [-o OUT.swu]
#        tools/make_swu.sh --genkey
#   -r ROOTFS   main rootfs.squashfs (default buildroot/output/images/rootfs.squashfs)
#   -k KERNEL   also write this kernel uImage to kernel2. PRIVATE use only:
#               the only kernel there is is Flashforge's (xImage-stock of a
#               private build), which must never be in a published update.
#               Without -k (the default) the update has no kernel and slot B
#               keeps the printer's own kernel (recovery checks it is there)
#   -K          no kernel (the default; kept for old command lines)
#   -V VERSION  version string (default: UTC date + rootfs sha256 prefix)
#   -o OUT      output file (default ./ad5x-main-VERSION.swu)
#   --zip       write a .zip instead (rootfs.squashfs, kernel.uimage, SHA256SUMS,
#               version.txt); the recovery OS installs it like a .swu
#   --both      write both, side by side
#   -s, --sign  sign it (.swu only) (only for a recovery built with signing, see below)
#   --genkey    create the signing key pair at $AD5X_SWU_KEY (see below)
#
# Unsigned by default (the recovery OS is open; every artifact still has its
# sha256 in sw-description). Signing key, only with --sign: AD5X_SWU_KEY, default ~/.config/ad5x/swupdate-private.pem
# (RSA-2048, PEM: SWUpdate's mbedTLS backend takes 256-byte signatures only).
# It never goes into the repository; this script refuses a key
# inside it. Make one with --genkey, or by hand:
#   mkdir -p ~/.config/ad5x && chmod 700 ~/.config/ad5x
#   openssl genrsa -out ~/.config/ad5x/swupdate-private.pem 2048
#   openssl rsa -in ~/.config/ad5x/swupdate-private.pem -pubout \
#       -out ~/.config/ad5x/swupdate-public.pem
# The recovery image carries the public key (board/ad5x-recovery/post-build.sh
# reads AD5X_SWU_PUBKEY or ~/.config/ad5x/swupdate-public.pem).
#
# The .swu (cpio, "crc" format): sw-description (libconfig), its RSA
# PKCS#1.5/SHA-256 signature sw-description.sig, the script ad5x-slot-b.sh
# (buildroot/package/ad5x-recovery/swupdate), kernel.uimage, rootfs.squashfs.
# Every artifact has its sha256 in the signed sw-description.
set -euo pipefail
REPO=$(cd "$(dirname "$0")/.." && pwd)
IMG=$REPO/buildroot/output/images
ROOTFS=$IMG/rootfs.squashfs
KERNEL=
NOKERNEL=1 VERSION= OUT= SIGN= FORMAT=swu
KEY=${AD5X_SWU_KEY:-$HOME/.config/ad5x/swupdate-private.pem}
SCRIPT=$REPO/buildroot/package/ad5x-recovery/swupdate/ad5x-slot-b.sh
GEN=$REPO/buildroot/package/ad5x-recovery/swupdate/mk-sw-description.sh
usage() { sed -n '2,32p' "$0" >&2; exit 2; }
die() { echo "make_swu: $*" >&2; exit 1; }

inside_repo() { case "$(realpath -m "$1")/" in "$REPO"/*) return 0 ;; esac; return 1; }

if [ "${1:-}" = --genkey ]; then
	inside_repo "$KEY" && die "refusing a key inside the repository: $KEY"
	[ -e "$KEY" ] && die "$KEY exists"
	mkdir -p "$(dirname "$KEY")"; chmod 700 "$(dirname "$KEY")"
	(umask 077; openssl genrsa -out "$KEY" 2048 2>/dev/null)
	openssl rsa -in "$KEY" -pubout -out "${KEY%-private.pem}-public.pem" 2>/dev/null ||
		openssl rsa -in "$KEY" -pubout -out "$KEY.pub"
	echo "make_swu: private key $KEY, public key next to it"
	exit 0
fi
ARGS=()
for a in "$@"; do
	case "$a" in --sign) SIGN=1 ;; --zip) FORMAT=zip ;; --both) FORMAT=both ;; *) ARGS+=("$a") ;; esac
done
set -- "${ARGS[@]+"${ARGS[@]}"}"
while getopts "r:k:KV:o:sh" o; do
	case $o in
	s) SIGN=1 ;;
	r) ROOTFS=$OPTARG ;; k) KERNEL=$OPTARG NOKERNEL= ;; K) NOKERNEL=1 KERNEL= ;;
	V) VERSION=$OPTARG ;; o) OUT=$OPTARG ;; *) usage ;;
	esac
done

if [ -n "$SIGN" ]; then
	[ -f "$KEY" ] || die "no signing key $KEY (AD5X_SWU_KEY); make one: $0 --genkey"
	inside_repo "$KEY" && die "refusing a key inside the repository: $KEY"
	openssl rsa -in "$KEY" -noout -text 2>/dev/null | grep -q 'Private-Key: (2048 bit' ||
		die "$KEY must be an RSA-2048 private key (SWUpdate with mbedTLS verifies 256-byte signatures only)"
fi
[ -f "$ROOTFS" ] || die "no $ROOTFS"
[ "$(head -c 4 "$ROOTFS")" = hsqs ] || die "$ROOTFS is not a squashfs image"
RSIZE=$(stat -c %s "$ROOTFS")
[ "$RSIZE" -le $((204800 * 512)) ] || die "rootfs $RSIZE bytes > the 100 MiB slot"
RSHA=$(sha256sum "$ROOTFS" | cut -d' ' -f1)
US=$REPO/buildroot/output/host/bin/unsquashfs
command -v unsquashfs >/dev/null && US=unsquashfs
if [ -x "$US" ] || command -v "$US" >/dev/null; then
	LIST=$("$US" -l "$ROOTFS" 2>/dev/null)
	grep -qx 'squashfs-root/etc/ad5x-release' <<<"$LIST" ||
		die "$ROOTFS has no /etc/ad5x-release (not a Kiln OS root)"
	grep -qx 'squashfs-root/linuxrc' <<<"$LIST" || die "$ROOTFS has no /linuxrc"
	! grep -qx 'squashfs-root/etc/ad5x-recovery' <<<"$LIST" ||
		die "$ROOTFS is the recovery OS, not the main OS"
fi
if [ -z "$NOKERNEL" ]; then
	[ -f "$KERNEL" ] || die "no $KERNEL"
	[ "$(od -An -t x1 -N 4 "$KERNEL" | tr -d ' \n')" = 27051956 ] || die "$KERNEL is not a uImage"
	KSIZE=$(stat -c %s "$KERNEL")
	[ "$KSIZE" -le $((16384 * 512)) ] || die "kernel $KSIZE bytes > the 8 MiB slot"
	KSHA=$(sha256sum "$KERNEL" | cut -d' ' -f1)
fi
[ -n "$VERSION" ] || VERSION=$(date -u +%Y%m%d%H%M)-${RSHA:0:8}
OUT=${OUT:-$PWD/ad5x-main-$VERSION.swu}
OUT=${OUT%.zip}; OUT=${OUT%.swu}.swu
ZOUT=${OUT%.swu}.zip

W=$(mktemp -d "${TMPDIR:-/tmp}/make_swu.XXXXXX")
trap 'rm -rf "$W"' EXIT
cp "$SCRIPT" "$W/ad5x-slot-b.sh"
ln -s "$(realpath "$ROOTFS")" "$W/rootfs.squashfs"
FILES="sw-description ad5x-slot-b.sh"
[ -n "$SIGN" ] && FILES="sw-description sw-description.sig ad5x-slot-b.sh"
if [ -z "$NOKERNEL" ]; then
	ln -s "$(realpath "$KERNEL")" "$W/kernel.uimage"
	FILES="$FILES kernel.uimage"
	sh "$GEN" "$VERSION" "$W/rootfs.squashfs" "$W/ad5x-slot-b.sh" "$W/kernel.uimage" > "$W/sw-description"
else
	sh "$GEN" "$VERSION" "$W/rootfs.squashfs" "$W/ad5x-slot-b.sh" > "$W/sw-description"
fi
FILES="$FILES rootfs.squashfs"
if [ -n "$SIGN" ]; then
	openssl dgst -sha256 -sign "$KEY" -out "$W/sw-description.sig" "$W/sw-description"
	openssl rsa -in "$KEY" -pubout -out "$W/pub.pem" 2>/dev/null
	openssl dgst -sha256 -verify "$W/pub.pem" -signature "$W/sw-description.sig" \
		"$W/sw-description" >/dev/null || die "signature check failed"
fi
if [ "$FORMAT" != zip ]; then
	(cd "$W" && printf '%s\n' $FILES | cpio -o -L -H crc --quiet) > "$OUT"
	echo "make_swu: $OUT ($(stat -c %s "$OUT") bytes), version $VERSION"
fi
if [ "$FORMAT" != swu ]; then
	command -v zip >/dev/null || die "zip not installed"
	echo "Kiln OS main system, version $VERSION" > "$W/version.txt"
	ZF="rootfs.squashfs"; [ -z "$NOKERNEL" ] && ZF="kernel.uimage $ZF"
	(cd "$W" && sha256sum $ZF > SHA256SUMS && rm -f "$ZOUT" && \
		zip -q -0 "$ZOUT" version.txt SHA256SUMS $ZF)
	echo "make_swu: $ZOUT ($(stat -c %s "$ZOUT") bytes, zip), version $VERSION"
fi
echo "  rootfs  $RSIZE bytes  sha256 $RSHA"
if [ -n "$NOKERNEL" ]; then
	echo "  no kernel: slot B keeps the printer's own"
else
	echo "  kernel  $KSIZE bytes  sha256 $KSHA  (PRIVATE: never publish this file)"
fi
if [ -n "$SIGN" ]; then
	echo "  signed with $KEY (public key fingerprint: $(openssl pkey -pubin -in "$W/pub.pem" -outform DER | sha256sum | cut -c1-16))"
else
	echo "  unsigned (sha256 per artifact)"
fi
