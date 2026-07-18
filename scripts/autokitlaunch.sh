#!/system/bin/sh
# autokitlaunch.sh - launch AutoKit once Android has fully booted
# Package found via: pm list packages -3   (Carlinkit AutoKit = cn.manstep.phonemirrorBox)
# Activity found via: cmd package resolve-activity --brief cn.manstep.phonemirrorBox
#
# Tune "sleep 5" upward (e.g. 10) if AutoKit opens before the CCPA
# dongle has enumerated and lands on a "waiting for device" screen.

while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done
sleep 5
am start -n cn.manstep.phonemirrorBox/.MainActivity 2>/dev/null
