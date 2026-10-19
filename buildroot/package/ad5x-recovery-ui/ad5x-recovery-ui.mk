################################################################################
#
# ad5x-recovery-ui
#
################################################################################

# Source in the repo (recovery-ui/, also builds on the laptop: see its
# Makefile). Laptop build output in recovery-ui/build is left out.
AD5X_RECOVERY_UI_VERSION = 1
AD5X_RECOVERY_UI_SITE = $(BR2_EXTERNAL_AD5X_PATH)/../recovery-ui
AD5X_RECOVERY_UI_SITE_METHOD = local
AD5X_RECOVERY_UI_OVERRIDE_SRCDIR_RSYNC_EXCLUSIONS = --exclude=/build
AD5X_RECOVERY_UI_LICENSE = GPL-3.0, OFL-1.1 (Noto Sans fonts)
AD5X_RECOVERY_UI_LICENSE_FILES = fonts/OFL-1.1.txt
AD5X_RECOVERY_UI_DEPENDENCIES = ad5x-lvgl

# fbdev + evdev back end, LVGL compiled in from ad5x-lvgl's sources
AD5X_RECOVERY_UI_MAKE_OPTS = \
	BACKEND=fbdev \
	O=$(@D)/out \
	LVGL_DIR=$(AD5X_LVGL_DIR) \
	CC="$(TARGET_CC)" \
	CFLAGS="$(TARGET_CFLAGS)" \
	LDFLAGS="$(TARGET_LDFLAGS)"

# SWUpdate's own progress client library when SWUpdate is in the image
# (it installs libswupdate.so and progress_ipc.h); otherwise the UI's
# built-in copy of the same socket protocol.
ifeq ($(BR2_PACKAGE_SWUPDATE),y)
AD5X_RECOVERY_UI_DEPENDENCIES += swupdate
AD5X_RECOVERY_UI_MAKE_OPTS += USE_LIBSWUPDATE=1
endif

define AD5X_RECOVERY_UI_BUILD_CMDS
	$(TARGET_MAKE_ENV) $(MAKE) -C $(@D) $(AD5X_RECOVERY_UI_MAKE_OPTS)
endef

define AD5X_RECOVERY_UI_INSTALL_TARGET_CMDS
	$(INSTALL) -D -m 0755 $(@D)/out/ad5x-recovery-ui \
		$(TARGET_DIR)/usr/bin/ad5x-recovery-ui
endef

$(eval $(generic-package))
