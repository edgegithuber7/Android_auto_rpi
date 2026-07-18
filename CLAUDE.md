# CLAUDE.md — Pi 5 Android Auto Head Unit

Context file for Claude Code. This repo manages a working DIY Android Auto
head unit. Read this before touching anything.

## The build

- **Hardware**: Raspberry Pi 5, USB SSD boot, 10.1" HDMI touchscreen
  (WCH/wch.cn USB touch controller, Vendor `27c0` Product `0859`, 15-point MT),
  USB combo audio device (DAC playback + mic capture, one USB device),
  Carlinkit CPC200-CCPA wireless Android Auto dongle, aux into car stereo.
- **OS**: KonstaKANG LineageOS 22.2 (Android 15) for Pi 5.
  SELinux is **permissive** (`androidboot.selinux=permissive` in cmdline),
  which is why plain `/system/etc/init/*.rc` services work without policy.
- **AutoKit app**: package `cn.manstep.phonemirrorBox`, activity `.MainActivity`.
- **Phone**: Pixel, wireless AA on 5 GHz channel 149 (non-DFS, keep it that way).

## Device-specific constants (do not guess — these were measured)

| Thing | Value |
|---|---|
| DAC ALSA card | 2 (`/dev/snd/pcmC2D0p` playback, `pcmC2D0c` capture) |
| tinymix ctl 2 | Mic Capture Switch (BOOL) |
| tinymix ctl 3 | Mic Capture Volume (INT, max 100) |
| tinymix ctl 4 | Headphone Playback Switch (BOOL) |
| tinymix ctl 5 | Headphone Playback Volume (INT, **2 channels**, max 100) |
| Media stream (3) max | 25 |
| Touch controller | Vendor 27c0 Product 0859, two interfaces (MT touchscreen + mouse emulation) |

## Hard-won gotchas (violating these caused real breakage)

1. **This tinymix takes integers, not percentages.** `tinymix -D 2 5 100 100`,
   never `100%` ("only enum types can be set with strings").
2. **No `media` binary on LOS 22.2.** Use `cmd media_session volume --stream N --get/--set`.
3. **`/boot/cmdline.txt` must remain ONE line.** A line break bricks boot.
   Always: print, copy whole line, rewrite with parameter appended, `cat` to verify.
4. **Do not set the media slider on a timer/loop unconditionally** — each `--set`
   audibly interrupts playback on this build. volumefix.sh reads first, sets only
   if the value dropped. Preserve this pattern.
5. **`adb root` drops the connection** (adbd restarts). Reconnect after. Root does
   not survive reboot. `adb shell whoami` to check.
6. **Quoting across `adb shell` one-liners**: wrap the whole remote command in
   single quotes, or use tinymix control numbers to avoid quotes entirely.
7. **Android stores volume PER OUTPUT DEVICE and PER STREAM.** Media = stream 3,
   voice call = stream 0 (currently NOT pinned — known issue: quiet calls).
   The DAC enumerating late at boot is why fixed-delay automation fails.
8. **Pi 5 advertises HDR over HDMI; the panel latches and locks its OSD.**
   Fixed by `hdmi_ignore_hdr=1` (config_user.txt) + `vc4.force_max_bpc=8` (cmdline)
   + panel OSD HDR=Off. Pi 4 does not have this problem.
9. **USB autosuspend default (2s) caused audio dropouts.** Fixed by
   `usbcore.autosuspend=-1` in cmdline.
10. **The safe-volume/CSD system actively re-lowers "headphone" volume.**
    Bypassed via `audio.safemedia.bypass=true` (build.prop) +
    `audio_safe_csd_enabled=0`, `audio_safe_volume_state=2` (settings).

## Repo layout

- `scripts/` — shell scripts installed to `/system/bin/` (755)
- `init/` — init service definitions installed to `/system/etc/init/` (644).
  Disable mechanism = rename `.rc` → `.rc.disabled` (init ignores non-.rc).
- `idc/` — input device config installed to `/system/usr/idc/` (644)
- `boot/` — snippets to apply manually to the boot partition / build.prop
- `tools/headunit.sh` — ADB installer + per-service enable/disable CLI
- `docs/` — full build & troubleshooting guide

## Known open items

- **Call quality**: calls reported quiet; stream 0 (voice call) is not pinned.
  Candidate fix is one line in volumefix.sh (commented placeholder exists).
  Crackle from the Pi 4 era is believed fixed by Pi 5 + autosuspend, unverified.
- **Multitouch inside Android Auto**: local MT works (IDC fix); the CCPA/AutoKit
  layer does not forward multi-point. Options: CCPA firmware update, or
  Headunit Reloaded (HUR) app replacing AutoKit (reads touch natively).
- **Planned GUI**: a desktop app wrapping tools/headunit.sh (download OS image,
  edit scripts, per-service toggles). The CLI was written to be its backend.

## Conventions

- Australian English in docs. Scripts are POSIX sh (Android's /system/bin/sh —
  no bashisms). Every on-device path change goes through tools/headunit.sh or
  gets documented in boot/ so a re-flash can be fully reconstructed.
