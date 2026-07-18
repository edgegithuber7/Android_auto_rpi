**Raspberry Pi 5 Android Auto Head Unit**

Complete Build & Configuration Guide

*LineageOS 22.2 (Android 15) · KonstaKANG build · Carlinkit CPC200-CCPA
· AutoKit*

Covers: SSD boot, USB DAC volume automation, HDMI/HDR panel fixes,
multitouch, wireless Android Auto tuning, auto-launch on boot, RTC, and
troubleshooting

July 2026

Contents

1\. Project Overview

This guide documents a DIY Android Auto head unit built around a
Raspberry Pi 5 running LineageOS, driving a 10-inch HDMI touchscreen,
with audio fed into the car’s stereo via a USB DAC and aux input, and
wireless Android Auto provided by a Carlinkit CPC200-CCPA adapter
running the AutoKit app.

It captures the complete working configuration, including every fix
developed along the way: automatic volume management for the USB DAC,
boot-time reduction, HDMI/HDR display quirks, multitouch enablement,
wireless stability tuning, automatic AutoKit launch, and a hardware
real-time clock.

1.1 Final architecture

- Raspberry Pi 5 running KonstaKANG LineageOS 22.2 (Android 15), booting
  from a USB SSD.

- 10.1-inch HDMI touchscreen (WCH-controller USB touch, 15-point
  capable) at 1920×1080 output.

- USB combo audio device (DAC output + microphone capture on one device)
  feeding the car’s aux input.

- Carlinkit CPC200-CCPA dongle + AutoKit APK (package
  cn.manstep.phonemirrorBox) providing wireless Android Auto on 5 GHz.

- Init scripts (volumefix, autokitlaunch) that make the unit fully
  hands-free from cold boot.

1.2 Why these choices

- Pi 5 over Pi 4: roughly 2–3× faster CPU, better USB controller
  architecture (helps full-duplex call audio), and much faster boot from
  SSD/NVMe.

- LineageOS 22.2 over 21 or 23.2: about a year of maturity, stable USB
  audio behaviour, and good AutoKit compatibility. LineageOS 23.2
  (Android 16) introduced a rewritten audio HAL — wait for it to shake
  out before migrating, and note OTA from pre-2026 builds is not
  possible (clean install required).

- SSD over SD card: the single biggest boot-time win, plus far better
  reliability for a device that gets power-cycled every drive.

2\. Parts & Software Checklist

2.1 Hardware

| **Item**                        | **Notes**                                                                                                                                                       |
|---------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Raspberry Pi 5 (4 GB+)          | Official 27 W (5 V/5 A) USB-C supply for bench work; the in-car 12 V→5 V converter must genuinely sustain 5 A or you will see audio glitches and throttling.    |
| USB SSD (or NVMe + HAT)         | Boot drive. Flash the LineageOS image directly onto it.                                                                                                         |
| 10.1″ HDMI touchscreen          | USB touch interface. This build used a Magedok panel with a WCH (Vendor 27c0, Product 0859) touch controller — 15-point capacitive.                             |
| USB DAC with mic (combo device) | Presents as one USB card with playback and capture. Feeds car aux; mic used for calls/assistant.                                                                |
| Carlinkit CPC200-CCPA           | Wireless CarPlay + wireless Android Auto dongle for Android head units. (The CCPW sibling model only does wired Android Auto — do not substitute.)              |
| Raspberry Pi 5 RTC battery      | Official Panasonic ML-2020 with 2-pin plug, ~AU\$8–10 (Core Electronics SKU CE09774). Plugs into the BAT connector; recharges itself whenever the Pi has power. |
| Short USB extension cable       | Optional but recommended: moves the CCPA away from USB 3/SSD RF noise if wireless dropouts appear.                                                              |

2.2 Software

| **Item**                           | **Where**                                                                                   |
|------------------------------------|---------------------------------------------------------------------------------------------|
| LineageOS 22.2 for Pi 5            | konstakang.com/devices/rpi5/ (unofficial KonstaKANG build; personal use licence).           |
| KonstaKANG-rpi-resize.zip          | Same site — expands the data partition to fill the drive; flash via TWRP.                   |
| AutoKit APK                        | carlinkit.com/download.html — use the newest (2025.03.19.1126 or later at time of writing). |
| Raspberry Pi Imager / balenaEtcher | For flashing the image to the SSD from your computer.                                       |
| ADB (platform-tools)               | On the Mac: brew install android-platform-tools.                                            |
| F-Droid (optional)                 | Open-source app store on the head unit; gateway to Aurora Store, OsmAnd, file managers.     |

3\. Flashing & First Boot

1.  Download the LineageOS 22.2 Pi 5 image from KonstaKANG and verify
    the SHA-256 checksum.

2.  Flash the image to the SSD with Raspberry Pi Imager or balenaEtcher
    (exactly as you would an SD card).

3.  Open the SSD’s boot partition (the FAT32 one visible to
    Windows/macOS) and set the boot device overlay in config.txt:

> \# Boot device
>
> \#dtoverlay=android-sdcard
>
> dtoverlay=android-usb
>
> \#dtoverlay=android-nvme

Exactly one overlay line should be uncommented: android-usb for a USB
SSD, android-nvme for an NVMe HAT. Boot with no SD card inserted.

4.  If your panel is not natively 1920×1080, put its native resolution
    in resolution.txt on the same partition (the build defaults to 1080p
    and requires EDID).

5.  Boot the Pi. First boot is slow — let it finish.

6.  Enable Developer options: Settings → About tablet → tap Build number
    seven times. Then in Developer options enable Rooted debugging and
    ADB over network.

7.  Boot to TWRP recovery (Settings → System → Raspberry Pi settings)
    and flash KonstaKANG-rpi-resize.zip so the data partition uses the
    whole drive.

8.  Install the AutoKit APK (sideload from the CCPA’s U-disk mode, a USB
    stick, or a browser download) and complete the Carlinkit pairing per
    its manual. In AutoKit’s settings enable Auto Connect and select a 5
    GHz non-DFS Wi-Fi channel (36–48 or 149–165).

> **Note:** This build ships with androidboot.selinux=permissive on the
> kernel command line, which is why the init scripts in this guide run
> without SELinux policy work. If a future build enforces SELinux,
> install Magisk (see KonstaKANG FAQ) and place scripts in
> /data/adb/service.d/ instead.

4\. ADB Fundamentals (Read This First)

Nearly every fix in this guide is applied over ADB from a computer.
Three rules prevent 90% of the mistakes made during this project:

Rule 1 — know which machine you are typing on

Your computer’s prompt (e.g. sam@Macbook ~ %) means commands run on the
computer. The Pi’s shell prompt (rpi5:/ \#) appears only after adb
shell. Any command touching /system, /boot or /dev must be typed at the
Pi prompt — pasting heredocs at the computer prompt writes files to your
computer (or errors) and silently does nothing on the Pi.

Rule 2 — root does not survive a reboot

> adb connect \<pi-ip\>:5555
>
> adb root
>
> adb connect \<pi-ip\>:5555 \# adbd restarts as root and drops the
> link - reconnect
>
> adb remount \# only needed when editing /system or /vendor
>
> adb shell whoami \# "root" = elevated, "shell" = not

Rule 3 — quoting across the ADB hop

One-liner commands with quotes must be wrapped in single quotes so the
local shell does not strip them: adb shell 'tinymix -D 2 "Headphone
Playback Volume" 100'. Better still, use control numbers instead of
names (no quoting at all). Inside an interactive adb shell session none
of this applies.

> **Note:** The error “protocol fault” immediately after adb root is
> usually harmless — the daemon restarted mid-handshake. Reconnect and
> carry on.

5\. USB DAC Volume: Full Volume on Every Boot & Reconnect

5.1 The problem

Android classifies the USB DAC as headphones. Two separate volume stages
start low: the DAC’s own hardware gain (ALSA mixer), and Android’s
per-device media volume, which Android restores at its saved (low) level
every time the DAC enumerates — which happens several seconds after
boot, defeating any fixed-delay automation such as MacroDroid.

5.2 Identify your DAC’s card and controls

> adb shell ls /dev/snd/ \# run with DAC plugged and unplugged;
>
> \# the pcmC?D0p entries that vanish are the DAC
>
> adb shell tinymix -D 2 \# list mixer controls (replace 2 with your
> card)

In this build the DAC is card 2 (pcmC2D0p playback, pcmC2D0c capture — a
combo device) with these controls:

| **Ctl** | **Control**                                          |
|---------|------------------------------------------------------|
| 2       | Mic Capture Switch (BOOL)                            |
| 3       | Mic Capture Volume (INT, max 100)                    |
| 4       | Headphone Playback Switch (BOOL)                     |
| 5       | Headphone Playback Volume (INT, 2 channels, max 100) |

> **Important:** This tinymix build takes plain integers, not
> percentages (“only enum types can be set with strings” if you try
> 100%). Two-channel controls take two values: tinymix -D 2 5 100 100.
> Card numbers follow USB enumeration order — if you ever add another
> USB audio device, re-check the card number.

5.3 Also required: the media slider command

LineageOS 22.2 has no media binary; the working command is cmd
media_session volume --stream 3 --set 25 (this build’s media stream
maxes at 25 — confirm yours with --get).

5.4 Also required: disable the “listening at high volume” cap

Android’s hearing-protection system does not just nag — it actively
drops the volume back down on “headphone” devices. Disable it for a
line-out head unit:

> adb root && adb remount
>
> adb shell 'echo audio.safemedia.bypass=true \>\> /system/build.prop'
>
> adb shell 'settings put global audio_safe_csd_enabled 0'
>
> adb shell 'settings put global audio_safe_volume_state 2'
>
> adb reboot

5.5 The volumefix service (final version)

A root init service that waits for the DAC device node, sets hardware
gain and mic level, sets the media slider once, then passively monitors:
it only re-issues the slider command if something lowered it (an
unconditional periodic set audibly interrupts playback on this build).
It also re-arms automatically every time the DAC reconnects.

At the Pi prompt (rpi5:/ \# after adb root / remount / shell), paste:

> cat \> /system/bin/volumefix.sh \<\< 'EOF'
>
> \#!/system/bin/sh
>
> DAC_NODE=/dev/snd/pcmC2D0p
>
> while true; do
>
> while \[ ! -e "\$DAC_NODE" \]; do sleep 1; done
>
> sleep 2
>
> tinymix -D 2 5 100 100 2\>/dev/null \# Headphone Playback Volume
>
> tinymix -D 2 4 1 2\>/dev/null \# Headphone Playback Switch
>
> tinymix -D 2 3 100 2\>/dev/null \# Mic Capture Volume
>
> tinymix -D 2 2 1 2\>/dev/null \# Mic Capture Switch
>
> cmd media_session volume --stream 3 --set 25 2\>/dev/null
>
> while \[ -e "\$DAC_NODE" \]; do
>
> vol=\$(cmd media_session volume --stream 3 --get 2\>/dev/null \| grep
> -o 'volume is \[0-9\]\*' \| grep -o '\[0-9\]\*\$')
>
> if \[ -n "\$vol" \] && \[ "\$vol" -lt 25 \]; then
>
> cmd media_session volume --stream 3 --set 25 2\>/dev/null
>
> fi
>
> sleep 10
>
> done
>
> done
>
> EOF
>
> chmod 755 /system/bin/volumefix.sh
>
> cat \> /system/etc/init/volumefix.rc \<\< 'EOF'
>
> service volumefix /system/bin/sh /system/bin/volumefix.sh
>
> class late_start
>
> user root
>
> EOF
>
> chmod 644 /system/etc/init/volumefix.rc
>
> exit

Then adb reboot. Verify and test:

> adb shell ps -A \| grep volumefix \# one line = service alive
>
> \# Test 1: cold boot, touch nothing, play music - must be at max
>
> \# Test 2: unplug/replug the DAC - back to max within ~4 seconds

- If 100 distorts through the aux input, use 95 95 on the control-5 line
  — some codecs clip at maximum into a line-in.

- Stop temporarily: adb shell 'stop volumefix'. Disable across reboots:
  rename the .rc to .rc.disabled. Remove: delete both files.

6\. Boot Time

- Boot from SSD (Section 3) — the dominant factor. The Android stack,
  not the Pi, is what made the Pi 4 feel slow; Pi 5 + SSD brings cold
  boot to roughly 30–40 seconds.

- Disable the boot animation: adb shell 'echo debug.sf.nobootanimation=1
  \>\> /system/build.prop' (root + remount first).

- Debloat unused system apps: pm list packages then pm disable-user
  --user 0 \<package\> for stock apps you never use. Avoid disabling
  anything you cannot identify.

- Keep user apps minimal — background services are the enemy of a
  fast-boot appliance. F-Droid, a browser, and a file manager are
  harmless; sync-heavy apps are not.

7\. Display: HDR Lockout, OSD Settings & Resolution

7.1 Greyed-out Brightness/Contrast (HDR latch)

The Pi 5 (unlike the Pi 4) advertises HDR capability in its HDMI
signalling. Budget panels with HDR set to “Auto” latch into HDR mode and
lock manual Brightness, Contrast, ECO, DCR and colour controls — only
Sharpness stays adjustable. Fix it from both ends:

Panel side

1.  Open the panel OSD → Other tab → set HDR from Auto to Off.

2.  Picture tab: set ECO to Standard and DCR to Off (DCR = dynamic
    contrast, which pumps the backlight scene-by-scene — awful on a
    mostly-white map, especially at night).

3.  Set Brightness/Contrast to taste. The panel stores these internally
    across power cycles. Many panels also use the bare up/down buttons
    as a direct brightness shortcut.

Pi side (stop the Pi advertising HDR at all)

At the Pi prompt, append to /boot/config_user.txt (survives OS updates,
unlike config.txt):

> cat \>\> /boot/config_user.txt \<\< 'EOF'
>
> \# Force SDR - stop panel latching into HDR
>
> hdmi_ignore_hdr=1
>
> EOF

Then add vc4.force_max_bpc=8 to the END of the single line in
/boot/cmdline.txt. Print the file first with cat, copy the whole line,
and rewrite it with the parameter appended:

> cat /boot/cmdline.txt
>
> echo '\<existing line exactly as printed\> vc4.force_max_bpc=8' \>
> /boot/cmdline.txt
>
> cat /boot/cmdline.txt \# verify: identical single line + new parameter
> at the end
>
> **Important:** cmdline.txt must remain ONE line. A stray line break
> here can prevent the Pi booting. Always print, copy, verify.

7.2 Render resolution and UI scale

Two different “resolutions” exist. The HDMI output resolution
(resolution.txt / EDID) should match the panel’s native mode. Android’s
render resolution can then be lowered for performance, and DPI raised
for glanceable in-car UI — instant, reversible, no root:

> adb shell wm size 1280x720 \# lighter GPU load; panel still receives
> native 1080p
>
> adb shell wm density 160 \# bigger number = bigger UI; tune in steps
> of 20
>
> adb shell wm size reset \# undo
>
> adb shell wm density reset
>
> **Note:** If the panel is 16:10 (e.g. 1280×800 native), forcing a 16:9
> render size letterboxes slightly. Match the aspect ratio if touch
> feels vertically offset.

8\. Multitouch

8.1 Diagnosis

> adb shell getevent -lp
>
> adb shell cat /proc/bus/input/devices

The WCH touch controller in this build exposes TWO interfaces with the
same IDs (Vendor 27c0, Product 0859): a genuine 15-slot multitouch
touchscreen (ABS_MT_SLOT max 14, ABS_MT_POSITION_X/Y, INPUT_PROP_DIRECT)
and a fallback mouse-emulation interface (BTN_MOUSE, REL_WHEEL). Android
favouring the mouse interface is what makes a perfectly capable panel
behave as single-touch.

8.2 Fix: input device configuration (IDC) file

At the Pi prompt (root + remount), using YOUR vendor/product IDs in
lowercase hex:

> cat \> /system/usr/idc/Vendor_27c0_Product_0859.idc \<\< 'EOF'
>
> touch.deviceType = touchScreen
>
> touch.orientationAware = 1
>
> device.internal = 1
>
> EOF
>
> chmod 644 /system/usr/idc/Vendor_27c0_Product_0859.idc
>
> exit

Reboot, then verify locally: Developer options → Pointer location ON →
two fingers should draw two crosshair trails with a pointer count of 2.
Toggle it back off afterwards.

8.3 Multitouch inside Android Auto (AutoKit)

Local multitouch working does not guarantee pinch-zoom inside the
projected Android Auto session — the CCPA/AutoKit layer must forward
multi-point input, and Carlinkit does not document multitouch support
for the CCPA. In practice:

1.  Update the CCPA box firmware (via AutoKit’s update entry, or the
    192.168.43.1 web interface / USB method) and install the newest
    AutoKit APK from carlinkit.com/download.html.

2.  Re-test pinch-zoom in Google Maps within Android Auto.

3.  If it still does not forward, that is the dongle’s ceiling.
    Workarounds: (a) Google Maps’ one-finger double-tap-then-drag zoom
    covers the main use case; (b) Headunit Reloaded (HUR) — a
    third-party AA head-unit app that replaces AutoKit and reads touch
    natively, giving full multitouch/swipe; install its trial via Aurora
    Store (from F-Droid) to test without Google Play Services; (c) run
    navigation natively on the Pi (needs a USB GPS dongle and hotspot
    internet) where local multitouch already works.

9\. Wireless Android Auto: Dropouts & Stability

9.1 Isolate the layer first

Play something locally on the Pi (browser/local file). Local clean +
Android Auto dropping = the wireless phone↔CCPA link. Local dropping too
= the Pi’s USB/audio path (see §9.3).

9.2 Wireless-link fixes, in order of effectiveness

1.  Physical separation: put the CCPA on a short USB extension cable
    away from USB 3 ports and the SSD. USB 3 radiates broadband RF that
    swamps 2.4 GHz and can degrade marginal 5 GHz links — this is the
    single most effective fix.

2.  Fixed non-DFS 5 GHz channel in AutoKit (36–48 or 149–165). DFS
    channels (52–144) can be forced to vacate mid-drive by radar
    detection, causing periodic dropouts. This build uses 5 GHz / 149.

3.  Update CCPA firmware + AutoKit APK — changelogs repeatedly mention
    wireless audio stutter fixes.

4.  Phone placement in the car: dash mount or open tray beats
    pocket/armrest against metal.

5.  Only then, AutoKit’s audio buffer/delay setting (if your version
    exposes it): step up one notch at a time — buffers hide link hiccups
    at the cost of latency (noticeable on calls). “Start Delay” on the
    Other Settings page is NOT this — it is the connection delay; leave
    it at 0.

6.  Sanity anchor: test wired AA for two minutes. Flawless wired =
    confirmed wireless-link diagnosis.

9.3 Pi-side dropout causes (if local audio also glitches)

- USB autosuspend — the classic periodic-dropout cause. Check cat
  /sys/module/usbcore/parameters/autosuspend; a value like 2 means idle
  USB devices suspend after 2 seconds. Fix now with echo -1 \>
  /sys/module/usbcore/parameters/autosuspend (root) and make permanent
  by appending usbcore.autosuspend=-1 to the cmdline.txt single line
  (same careful procedure as §7.1).

- Power: vcgencmd get_throttled while audio plays — anything other than
  0x0 means the supply sags; the Pi 5 needs a genuine 5 A. On the bench
  with the official 27 W supply this is ruled out; in the car it is the
  prime suspect.

- Bus errors: dmesg \| grep -iE "usb\|xhci" \| tail -30 right after a
  dropout — repeated resets/disconnects point to cable or port.

- Anything that pokes the volume system rhythmically (an aggressive
  automation loop, an old MacroDroid macro) can itself interrupt
  playback — which is why volumefix only sets the slider when it has
  actually dropped.

10\. Phone Call Quality (Crackle)

Calls are the hardest audio case: full-duplex (mic capture + playback
simultaneously) with real-time resampling (call audio is 8/16 kHz; the
DAC runs 44.1/48 kHz). Checklist, easiest first:

1.  Re-test on the Pi 5 with USB autosuspend disabled (§9.3) — the
    improved USB architecture plus that fix resolves many cases
    outright.

2.  Power under call load: vcgencmd get_throttled during a call.
    Undervoltage = crackle. Powered USB hub for the DAC/mic, and a
    genuinely 5 A car supply.

3.  Mic gain: the volumefix script pins Mic Capture Volume at 100. If
    the codec supports boost beyond 100, do not use it — boost on these
    chips distorts into crackle.

4.  AutoKit mic mode: toggle between box mic and Android mic. Routing
    call audio through the CCPA’s own path takes the USB combo device
    out of the capture chain entirely, halving its full-duplex workload.

5.  Sample-rate lock: as a last resort, edit the USB profile in
    /vendor/etc/audio_policy_configuration.xml to pin the capture path
    at 16000 Hz. Take a backup first; this file varies by build.

6.  If all else fails, a different cheap USB mic/DAC — some codecs
    misreport supported rates and no configuration fixes them.

> **Note:** Android Auto’s hidden developer settings on the phone (tap
> the version number in AA settings repeatedly) include Save Audio /
> Save Microphone Input, which capture what actually crosses the link —
> useful for proving whether garbage enters on the mic leg or the
> playback leg.

11\. Auto-Launch AutoKit on Boot

AutoKit’s package is cn.manstep.phonemirrorBox (found via pm list
packages -3; confirm the launch activity with cmd package
resolve-activity --brief). A separate oneshot init service launches it
once Android reports boot complete — kept independent of volumefix so it
can be disabled on its own.

At the Pi prompt (root + remount):

> cat \> /system/bin/autokitlaunch.sh \<\< 'EOF'
>
> \#!/system/bin/sh
>
> while \[ "\$(getprop sys.boot_completed)" != "1" \]; do sleep 2; done
>
> sleep 5
>
> am start -n cn.manstep.phonemirrorBox/.MainActivity 2\>/dev/null
>
> EOF
>
> chmod 755 /system/bin/autokitlaunch.sh
>
> cat \> /system/etc/init/autokitlaunch.rc \<\< 'EOF'
>
> service autokitlaunch /system/bin/sh /system/bin/autokitlaunch.sh
>
> class late_start
>
> user root
>
> oneshot
>
> EOF
>
> chmod 644 /system/etc/init/autokitlaunch.rc
>
> exit

- Tune the sleep 5: increase to 10 if AutoKit opens before the CCPA has
  enumerated (“waiting for device”).

- Disable without deleting: mv /system/etc/init/autokitlaunch.rc
  /system/etc/init/autokitlaunch.rc.disabled (init ignores non-.rc
  files); mv back to re-enable.

Result: power on → volumefix pins audio → autokitlaunch opens the app →
phone auto-connects (AutoKit’s Auto Connect must be ON). Fully
hands-free.

12\. Real-Time Clock (Time Survives Power-Off)

The Pi has no battery-backed clock by default, so time resets on cold
boot, and NTP cannot correct it until the phone link provides internet.
The Pi 5, however, has an RTC on board — it only needs the official
battery.

1.  Buy the official Raspberry Pi 5 RTC battery (Panasonic ML-2020,
    2-pin plug, ~AU\$8–10; Core Electronics SKU CE09774 — note AU
    checkout requires a short button-cell declaration).

2.  With the Pi powered off, plug it into the small 2-pin BAT connector
    on the board edge and stick the cell down with the supplied pad.

3.  Boot, set the correct time once (Settings → System → Date & time;
    leave automatic sync ON so any internet corrects drift).

4.  Cold-boot test: time should survive. The cell recharges itself
    whenever the Pi is powered, so a regularly driven car maintains it
    indefinitely.

> **Note:** If the build does not restore from the hardware clock at
> boot, a two-line hwclock init script (same pattern as volumefix) fixes
> it — KonstaKANG 22.2 normally handles it natively.

13\. Troubleshooting Quick Reference

| **Symptom**                               | **Likely cause → fix**                                                                                                                                              |
|-------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Volume low after boot                     | volumefix not running → ps -A \| grep volumefix; check both files exist and getenforce says Permissive.                                                             |
| Slider maxed but output quiet             | DAC hardware gain → tinymix -D 2 5 should read 100 100; wrong control number/name otherwise.                                                                        |
| Volume drops mid-drive                    | Safe-volume system re-capping → verify §5.4 bypasses (getprop audio.safemedia.bypass = true, audio_safe_csd_enabled = 0). volumefix’s monitor also self-heals this. |
| Audio cuts out periodically               | USB autosuspend (check for -1) → §9.3; if only in Android Auto, wireless link → §9.2.                                                                               |
| “Invalid mixer control”                   | Quoting stripped across adb hop → single-quote the whole command or use control numbers.                                                                            |
| “only enum types can be set with strings” | This tinymix wants integers → 100 100, not 100%.                                                                                                                    |
| media: inaccessible or not found          | No media binary on 22.2 → use cmd media_session volume …                                                                                                            |
| Panel Brightness/Contrast greyed out      | HDR latched or ECO preset/DCR active → §7.1 (HDR Off, ECO Standard, DCR Off + Pi-side SDR forcing).                                                                 |
| Single-touch only                         | Controller’s mouse interface winning → IDC file (§8.2). Works locally but not in AA → CCPA forwarding limit (§8.3).                                                 |
| Time wrong every boot                     | No RTC battery → §12.                                                                                                                                               |
| heredoc/file commands “no such file”      | You are on the computer, not the Pi → adb shell first; look for rpi5:/ \#.                                                                                          |
| adb root then connection lost             | Normal — adbd restarts → adb connect again.                                                                                                                         |
| Pi will not boot after cmdline edit       | Line break or typo in cmdline.txt → mount the SSD boot partition on a computer and repair the single line.                                                          |
| Throttling / random weirdness in car      | vcgencmd get_throttled ≠ 0x0 → the 12 V→5 V supply cannot hold 5 A; replace it.                                                                                     |

13.1 Useful one-liners

> adb shell whoami \# root or shell?
>
> adb shell getenforce \# SELinux mode
>
> adb shell vcgencmd get_throttled \# power health (0x0 = good)
>
> adb shell ls /dev/snd/ \# audio cards present
>
> adb shell tinymix -D 2 \# DAC mixer state
>
> adb shell 'cmd media_session volume --stream 3 --get'
>
> adb shell dumpsys activity activities \| grep -i mResumedActivity \#
> foreground app
>
> adb shell 'ps -A --sort=-%mem \| head -15' \# top RAM users

14\. Inventory of Custom Files on the Pi

| **Path**                                     | **Purpose**                                                         |
|----------------------------------------------|---------------------------------------------------------------------|
| /system/bin/volumefix.sh                     | DAC gain + media-slider monitor loop (§5.5).                        |
| /system/etc/init/volumefix.rc                | Init service keeping volumefix alive.                               |
| /system/bin/autokitlaunch.sh                 | Launches AutoKit after boot completes (§11).                        |
| /system/etc/init/autokitlaunch.rc            | Oneshot init service for the above.                                 |
| /system/usr/idc/Vendor_27c0_Product_0859.idc | Classifies the WCH touch controller as a touchscreen (§8.2).        |
| /system/build.prop (appended)                | audio.safemedia.bypass=true; optionally debug.sf.nobootanimation=1. |
| /boot/config_user.txt (appended)             | hdmi_ignore_hdr=1 (§7.1).                                           |
| /boot/cmdline.txt (edited)                   | vc4.force_max_bpc=8 appended; optionally usbcore.autosuspend=-1.    |
| Settings database (global)                   | audio_safe_csd_enabled=0, audio_safe_volume_state=2.                |

*Everything above lives on the SSD, so re-flashing the OS means
re-applying this guide — keep this document with the project.*
