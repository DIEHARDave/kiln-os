# Kiln OS: which kernel runs (sourced).
#   KERNEL=stock  Flashforge's 5.10: out-of-tree drivers and board tools from
#                 /data/ad5x/vendor (S06ad5x-modules, S07ad5x-board)
#   KERNEL=own    our 6.6 (kernel-ingenic66/): drivers built in, the board
#                 through the standard interfaces (sysfs GPIO, backlight class)
# AD5X_KERNEL=stock|own overrides (tests on a PC)
case "${AD5X_KERNEL:-$(uname -r)}" in
stock|5.10.*) KERNEL=stock ;;
*) KERNEL=own ;;
esac
