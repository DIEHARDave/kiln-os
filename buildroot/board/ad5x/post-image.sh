#!/bin/sh
# Runs after the root filesystem images are made ($BINARIES_DIR).
# The image runs on the printer's own stock 5.10 kernel, which stays in its
# kernel partitions (updates carry no kernel). Only a private build
# (bundle-stock.sh: ad5x_bundle_vendor) copies the stock kernels next to the
# images, from AD5X_STOCK_KERNEL_DIR (default: the unpacked stock
# kernel-2.0.1 updater in firmware/); a vendor-free build removes them.
set -e
REPO=$(cd "$BR2_EXTERNAL_AD5X_PATH/.." && pwd)
. "$BR2_EXTERNAL_AD5X_PATH/board/ad5x/bundle-stock.sh"
K=${AD5X_STOCK_KERNEL_DIR:-$REPO/firmware/stock-3.1.0/unpacked/kernel-2.0.1}
rm -f "$BINARIES_DIR/xImage-stock" "$BINARIES_DIR/xImage-stock-sdnand"
if ad5x_bundle_vendor; then
	for v in ota_kernel:xImage-stock ota_kernel_sd:xImage-stock-sdnand; do
		src=$(ls "$K/${v%%:*}"/ota_v1/xImage.0000.* 2>/dev/null | head -1)
		if [ -n "$src" ]; then
			cp "$src" "$BINARIES_DIR/${v#*:}"
		else
			echo "post-image: WARNING no stock kernel in $K/${v%%:*}"
		fi
	done
fi
# USB test stick image: FAT (flashforge_init.sh) + ext4 root
USB=$BR2_EXTERNAL_AD5X_PATH/board/ad5x/usb
cp "$USB/flashforge_init.sh" "$BINARIES_DIR/"
cat > "$BINARIES_DIR/README.txt" <<'TXT'
Kiln OS, USB test mode. With this stick in, the printer starts our
system instead of the Flashforge app. Unplug and power-cycle for stock.
Log: ad5x-usb.log on this partition. Never put an AD5X-*.tgz here.
TXT
GENIMAGE_TMP=$BUILD_DIR/genimage.tmp
rm -rf "$GENIMAGE_TMP"
genimage --rootpath "$TARGET_DIR" --tmppath "$GENIMAGE_TMP" \
	--inputpath "$BINARIES_DIR" --outputpath "$BINARIES_DIR" \
	--config "$USB/genimage.cfg"

{
cat <<'TXT'
usb-test.img           USB test stick: write whole to a stick (dd)
rootfs.squashfs        our root filesystem (LZO squashfs, as stock)
rootfs.ext4            the same, ext4 (part of usb-test.img)
rootfs.tar             the same tree, for inspection or qemu tests
TXT
if ad5x_bundle_vendor; then
cat <<'TXT'
xImage-stock           stock Linux 5.10.186 (u-boot image), eMMC units
xImage-stock-sdnand    stock Linux 5.10.186, SD-NAND units
PRIVATE build: contains Flashforge/Ingenic files; never publish it.
TXT
else
echo "Vendor-free build: no Flashforge/Ingenic files (tools/check_vendor_free.sh)."
fi
echo "See buildroot/README.md."
} > "$BINARIES_DIR/IMAGES.txt"
