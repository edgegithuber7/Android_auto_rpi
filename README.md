# Pi 5 Android Auto Head Unit

A DIY wireless Android Auto head unit: Raspberry Pi 5 + KonstaKANG LineageOS
22.2 (Android 15) + 10.1" HDMI touchscreen + USB DAC into the car's aux +
Carlinkit CPC200-CCPA + AutoKit. Fully hands-free from cold boot: power on →
volume pinned → AutoKit launches → phone auto-connects.

This repo contains every customisation applied on top of a stock KonstaKANG
flash, an ADB-driven installer with per-service enable/disable, and the full
build & troubleshooting guide.

## Quick start (on an already-flashed Pi)

```bash
# prerequisites: adb installed; Pi has Rooted debugging + ADB over network on
./tools/headunit.sh connect 192.168.x.x
./tools/headunit.sh install
adb reboot
./tools/headunit.sh status
```

Boot-partition and build.prop changes are deliberately manual (they can brick
boot if done blind) — apply them from the snippets in `boot/`, following the
cmdline single-line warning.

## What each piece does

| Component | Problem it solves |
|---|---|
| `scripts/volumefix.sh` + `init/volumefix.rc` | Android treats the USB DAC as headphones and restores a low saved volume every time it enumerates (which is seconds after boot). This service watches the device node and pins DAC hardware gain + media volume on every boot and reconnect, then guards it passively. |
| `scripts/autokitlaunch.sh` + `init/autokitlaunch.rc` | Launches AutoKit automatically once `sys.boot_completed`, replacing unreliable timer-based automation. |
| `idc/Vendor_27c0_Product_0859.idc` | The WCH touch controller exposes both a 15-point touchscreen and a mouse-emulation interface; Android picks the mouse. This classifies it correctly → full local multitouch. |
| `boot/config_user.txt.additions` | `hdmi_ignore_hdr=1` — the Pi 5 advertises HDR, budget panels latch into it and lock their OSD brightness/contrast. |
| `boot/cmdline.txt.additions` | `vc4.force_max_bpc=8` (SDR signalling) and `usbcore.autosuspend=-1` (USB autosuspend caused periodic audio dropouts). |
| `boot/build.prop.additions` + `boot/settings.commands` | Disable the safe-volume/CSD system that actively re-lowers "headphone" volume. |
| `tools/headunit.sh` | Installer + `status` / `enable` / `disable` / `uninstall` for each service. Disable = rename `.rc` → `.rc.disabled`; nothing is lost. |

## Enable/disable individual services

```bash
./tools/headunit.sh disable autokitlaunch   # stop AutoKit auto-launching
./tools/headunit.sh enable autokitlaunch
./tools/headunit.sh status
```

## Docs

`docs/GUIDE.md` — the complete build guide: parts list, flashing, ADB
fundamentals, every fix with its diagnosis story, wireless tuning, call-quality
checklist, RTC battery, troubleshooting table, and the inventory of every
non-stock file on the device.

`CLAUDE.md` — condensed project context (device constants, gotchas, open
items) for AI-assisted development sessions.

## Porting to other hardware (e.g. Pi 4 / iPhone)

The scripts are hardware-parameterised — re-derive for the target device:
DAC card number (`ls /dev/snd/` plug/unplug), tinymix control numbers
(`tinymix -D <card>`), touch IDs (`/proc/bus/input/devices`), media stream max
(`cmd media_session volume --stream 3 --get`). Pi 4 differences: no HDR problem
(skip those boot changes), no onboard RTC, 5V/3A supply, slower boot. iPhone:
the CCPA does wireless CarPlay natively; same audio/call architecture applies.

## Licence / status

Personal project configuration. LineageOS images are KonstaKANG's unofficial
builds (see konstakang.com for their terms); AutoKit is Carlinkit's app.

Open items: voice-call stream (0) not yet pinned (quiet calls — one-line fix
commented in volumefix.sh); multitouch inside Android Auto blocked at the
CCPA forwarding layer (Headunit Reloaded is the known workaround).
