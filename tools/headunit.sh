#!/usr/bin/env bash
# headunit.sh - install / manage the Pi head-unit customisations over ADB
#
# Usage:
#   ./tools/headunit.sh connect <pi-ip>       # connect + root + remount
#   ./tools/headunit.sh install               # push scripts, rc files, idc
#   ./tools/headunit.sh status                # show what's installed/running
#   ./tools/headunit.sh enable <name>         # enable a service  (volumefix|autokitlaunch)
#   ./tools/headunit.sh disable <name>        # disable a service (renames .rc)
#   ./tools/headunit.sh uninstall             # remove all managed files
#
# Run from the repository root. Requires adb (brew install android-platform-tools).

set -euo pipefail
cd "$(dirname "$0")/.."

SERVICES=(volumefix autokitlaunch)

die() { echo "error: $*" >&2; exit 1; }

need_root() {
  local who
  who=$(adb shell whoami | tr -d '\r')
  [ "$who" = "root" ] || die "adb is not root - run: $0 connect <pi-ip>"
}

case "${1:-}" in
  connect)
    [ -n "${2:-}" ] || die "usage: $0 connect <pi-ip>"
    adb connect "$2:5555"
    adb root || true
    sleep 2
    adb connect "$2:5555"
    adb remount
    adb shell whoami
    ;;

  install)
    need_root
    for s in "${SERVICES[@]}"; do
      adb push "scripts/$s.sh" "/system/bin/$s.sh"
      adb shell chmod 755 "/system/bin/$s.sh"
      adb push "init/$s.rc" "/system/etc/init/$s.rc"
      adb shell chmod 644 "/system/etc/init/$s.rc"
    done
    for f in idc/*.idc; do
      adb push "$f" "/system/usr/idc/$(basename "$f")"
      adb shell chmod 644 "/system/usr/idc/$(basename "$f")"
    done
    echo "Installed. Reboot to activate: adb reboot"
    echo "NOTE: boot-partition and build.prop changes are manual - see boot/*.additions"
    ;;

  status)
    echo "--- services ---"
    for s in "${SERVICES[@]}"; do
      rc=$(adb shell "ls /system/etc/init/$s.rc 2>/dev/null" | tr -d '\r')
      dis=$(adb shell "ls /system/etc/init/$s.rc.disabled 2>/dev/null" | tr -d '\r')
      run=$(adb shell "ps -A | grep -c $s" | tr -d '\r')
      state="not installed"
      [ -n "$dis" ] && state="DISABLED"
      [ -n "$rc" ] && state="enabled"
      echo "$s: $state (processes: $run)"
    done
    echo "--- key checks ---"
    adb shell getprop audio.safemedia.bypass | sed 's/^/safemedia.bypass: /'
    adb shell 'cat /sys/module/usbcore/parameters/autosuspend' | sed 's/^/usb autosuspend: /'
    adb shell getenforce | sed 's/^/selinux: /'
    ;;

  enable)
    need_root
    [ -n "${2:-}" ] || die "usage: $0 enable <service>"
    adb shell "mv /system/etc/init/$2.rc.disabled /system/etc/init/$2.rc"
    echo "$2 enabled - takes effect next boot (adb reboot)"
    ;;

  disable)
    need_root
    [ -n "${2:-}" ] || die "usage: $0 disable <service>"
    adb shell "stop $2 2>/dev/null" || true
    adb shell "mv /system/etc/init/$2.rc /system/etc/init/$2.rc.disabled"
    echo "$2 disabled - will not start on next boot"
    ;;

  uninstall)
    need_root
    for s in "${SERVICES[@]}"; do
      adb shell "stop $s 2>/dev/null" || true
      adb shell "rm -f /system/bin/$s.sh /system/etc/init/$s.rc /system/etc/init/$s.rc.disabled"
    done
    for f in idc/*.idc; do
      adb shell "rm -f /system/usr/idc/$(basename "$f")"
    done
    echo "Removed managed files. build.prop / boot-partition changes are manual - see boot/"
    ;;

  *)
    grep '^#' "$0" | head -14 | sed 's/^# \{0,1\}//'
    ;;
esac
