# Pi Head Unit Manager (GUI)

A PyQt6 desktop app that wraps this repo's install/enable/disable flow
(previously only available via `tools/headunit.sh`). It reimplements that
flow natively in Python over `adb` - no bash/WSL required.

## What it does

- **Board selector**: Pi 4 or Pi 5 - filters which boot tweaks apply (the
  HDR-latching fix is Pi 5-only; see `CLAUDE.md`).
- **Connection**: connect / root / remount over ADB, with live status.
  Every write action is disabled until you're connected, rooted, *and*
  remounted.
- **Services**: shows each `scripts/<name>.sh` + `init/<name>.rc` pair found
  in the repo, with on-device status (installed/enabled/disabled/running)
  and enable/disable/install/uninstall buttons. New pairs added to the repo
  show up automatically - nothing is hardcoded to today's `volumefix` /
  `autokitlaunch`.
- **Boot changes**: the `/boot/cmdline.txt`, `/boot/config_user.txt`,
  `/system/build.prop`, and settings-db tweaks from `boot/*.additions`,
  filtered to the selected board. Apply always previews the exact change,
  backs up the current remote file/value first, writes, then reads back to
  verify. Revert restores the most recent backup.
- **Download**: opens the correct `konstakang.com/devices/rpi4` or `rpi5`
  page in your browser, or fetches a pasted direct mirror URL in-app with a
  resumable progress bar (we don't scrape the page - mirror links there
  aren't stable enough to parse).
- **Editor**: every managed script/rc/idc file in its own tab. **Save**
  writes the local repo file; **Push** sends just that file to the device.
  The two are always separate - editing never silently touches the device.
- **Install all / Uninstall all**: same effect as `tools/headunit.sh install`
  / `uninstall`, for every discovered service and idc file at once.

## Running it

```bash
pip install -r gui/requirements.txt
python -m gui.main
```

Requires `adb` (Android platform-tools) on your `PATH`. If it's missing, the
window still opens - you'll get a clear error the first time you try to
connect, rather than a crash on launch.

## Safety notes

- `cmdline.txt` is only ever read-modify-written as a single line, with a
  same-line verification read-back afterwards (CLAUDE.md gotcha #3: a stray
  line break there can prevent the Pi from booting).
- Every boot/build.prop/settings change is backed up under `gui/backups/`
  before it's written (`.gitignore`d - these are local device backups, not
  repo content).
- Uninstall (single service or "Uninstall all") always asks for confirmation
  first - it removes files from the device.
