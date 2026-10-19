################################################################################
#
# ad5x-lvgl
#
################################################################################

# LVGL sources only: users (ad5x-recovery-ui) build them with their own
# lv_conf.h from $(AD5X_LVGL_DIR), so nothing is built or installed here.
AD5X_LVGL_VERSION = 9.5.0
AD5X_LVGL_SITE = $(call github,lvgl,lvgl,v$(AD5X_LVGL_VERSION))
AD5X_LVGL_LICENSE = MIT
AD5X_LVGL_LICENSE_FILES = LICENCE.txt
AD5X_LVGL_INSTALL_TARGET = NO

$(eval $(generic-package))
