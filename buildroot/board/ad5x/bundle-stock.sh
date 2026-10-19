# Sourced by the post-build and post-image scripts of both images
# (board/ad5x and board/ad5x-recovery).
#
# ad5x_bundle_vendor: true when this build bundles Flashforge/Ingenic files
# (private builds): BR2_AD5X_BUNDLE_VENDOR=y in the configuration, unless the
# environment says AD5X_VENDOR_FREE=1 (or forces bundling with
# AD5X_VENDOR_FREE=0). The default is a vendor-free image: the printer uses its
# own copies in /data/ad5x/vendor (ad5x-vendor, docs/install.md).
#
# bundle_stock TARGET: in a private build, copies the stock kernel's driver
# modules (/module_driver) and stock's board tools (cmd_gpio, cmd_fb,
# cmd_jpeg_display and their Ingenic libraries, in
# /usr/lib/ad5x/stock-tools) from a local stock root filesystem
# (AD5X_STOCK_ROOTFS, default firmware/ff-repo/stock5x; never committed).
# In a vendor-free build it removes them. /usr/bin/cmd_* are our wrappers
# (package ad5x-system), which use either copy. /usr/lib/ad5x/vendor-mode
# records which: "bundled" or "none".
ad5x_bundle_vendor() {
	case "${AD5X_VENDOR_FREE:-}" in
	1|y|yes) return 1 ;;
	0|n|no) return 0 ;;
	esac
	grep -qx 'BR2_AD5X_BUNDLE_VENDOR=y' "${BR2_CONFIG:-/dev/null}" 2>/dev/null
}

bundle_stock() {
	_t=$1
	_repo=$(cd "$BR2_EXTERNAL_AD5X_PATH/.." && pwd)
	_stock=${AD5X_STOCK_ROOTFS:-$_repo/firmware/ff-repo/stock5x}
	_st=$_t/usr/lib/ad5x/stock-tools

	rm -rf "$_t/module_driver" "$_st"
	mkdir -p "$_t/usr/lib/ad5x"
	if ! ad5x_bundle_vendor; then
		echo none > "$_t/usr/lib/ad5x/vendor-mode"
		echo "post-build: vendor-free image (drivers and board tools from /data/ad5x/vendor on the printer)"
		return 0
	fi
	echo bundled > "$_t/usr/lib/ad5x/vendor-mode"
	echo "post-build: PRIVATE build, bundling Flashforge/Ingenic files from $_stock (not for release)"
	if [ -d "$_stock/module_driver" ]; then
		cp -a "$_stock/module_driver" "$_t/module_driver"
		echo "post-build: stock drivers from $_stock/module_driver"
	else
		echo "post-build: WARNING no $_stock/module_driver, image has no drivers"
	fi

	# Stock's board tools (Ingenic's libhardware2): cmd_gpio for the PC11
	# heartbeat, cmd_fb and cmd_jpeg_display for the display and boot logo.
	# Run with our libc through the /usr/bin wrappers.
	if [ -x "$_stock/usr/bin/cmd_gpio" ]; then
		mkdir -p "$_st/bin" "$_st/lib"
		for _b in cmd_gpio cmd_fb cmd_jpeg_display; do
			cp "$_stock/usr/bin/$_b" "$_st/bin/"
		done
		for _l in libhardware2.so libutils2.so libjpeg.so.9; do
			cp -L "$(find "$_stock/usr/lib" "$_stock/lib" -name $_l | head -1)" "$_st/lib/"
		done
		echo "post-build: stock board tools from $_stock"
	else
		echo "post-build: WARNING no stock board tools in $_stock"
	fi
}
