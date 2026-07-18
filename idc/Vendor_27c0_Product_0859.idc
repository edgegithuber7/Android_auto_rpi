# Input Device Configuration for the WCH (wch.cn) USB touch controller.
# Forces Android to treat it as a touchscreen (it also exposes a
# mouse-emulation interface that otherwise wins, giving single-touch).
# Filename MUST match the controller: Vendor_XXXX_Product_YYYY.idc
# (lowercase hex, from /proc/bus/input/devices).
# Install to /system/usr/idc/ (chmod 644), then reboot.
touch.deviceType = touchScreen
touch.orientationAware = 1
device.internal = 1
