"""Applies/reverts the boot-partition, build.prop, and settings-db tweaks
defined in profiles.py.

Every apply backs up the remote file (or the previous settings value) before
writing anything, matching the repo's existing caution around boot-partition
edits (README.md / CLAUDE.md gotcha #3: a bad cmdline.txt edit can brick boot).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .adb import AdbClient
from .profiles import BootItem, BootTarget

REMOTE_PATHS = {
    BootTarget.CMDLINE: "/boot/cmdline.txt",
    BootTarget.CONFIG_USER: "/boot/config_user.txt",
    BootTarget.BUILD_PROP: "/system/build.prop",
}


class BootManagerError(RuntimeError):
    pass


@dataclass
class ApplyPreview:
    """What an apply would do, for the confirmation dialog."""

    summary: str
    already_applied: bool


class BootManager:
    def __init__(self, backups_dir: Path):
        self.backups_dir = backups_dir
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self._settings_backup_file = self.backups_dir / "settings_backup.json"

    # -- status ------------------------------------------------------------

    def is_applied(self, adb: AdbClient, item: BootItem) -> bool:
        if item.target is BootTarget.SETTINGS:
            return adb.get_setting(item.setting_key) == item.setting_value
        if item.target is BootTarget.CMDLINE:
            line = adb.cat(REMOTE_PATHS[BootTarget.CMDLINE])
            return item.value in line.split()
        content = adb.cat(REMOTE_PATHS[item.target])
        return any(line.strip() == item.value for line in content.splitlines())

    # -- preview / apply / revert -------------------------------------------

    def preview_apply(self, adb: AdbClient, item: BootItem) -> ApplyPreview:
        if self.is_applied(adb, item):
            return ApplyPreview(f"'{item.value}' is already applied - no change needed.", True)
        if item.target is BootTarget.SETTINGS:
            current = adb.get_setting(item.setting_key)
            summary = (
                f"Run: settings put global {item.setting_key} {item.setting_value}\n"
                f"(current value: {current!r} - will be backed up for revert)"
            )
        elif item.target is BootTarget.CMDLINE:
            line = adb.cat(REMOTE_PATHS[BootTarget.CMDLINE]).strip()
            summary = (
                "Append to the single line in /boot/cmdline.txt "
                "(backed up first):\n\n"
                f"  {line} {item.value}\n"
            )
        else:
            path = REMOTE_PATHS[item.target]
            summary = f"Append this line to {path} (backed up first):\n\n  {item.value}\n"
        return ApplyPreview(summary, False)

    def apply(self, adb: AdbClient, item: BootItem) -> None:
        if not adb.ready_to_write:
            raise BootManagerError("device must be connected, rooted, and remounted first")
        if self.is_applied(adb, item):
            return

        if item.target is BootTarget.SETTINGS:
            previous = adb.get_setting(item.setting_key)
            self._record_setting_backup(item.setting_key, previous)
            adb.put_setting(item.setting_key, item.setting_value)
            if adb.get_setting(item.setting_key) != item.setting_value:
                raise BootManagerError(f"verification failed after writing {item.key}")
            return

        if item.target is BootTarget.CMDLINE:
            path = REMOTE_PATHS[BootTarget.CMDLINE]
            original = adb.cat(path)
            line = original.strip("\n")
            if "\n" in line:
                raise BootManagerError(
                    "cmdline.txt is not a single line on-device - refusing to touch it"
                )
            self._backup(item.target, original)
            adb.write_text(path, f"{line} {item.value}\n")
            verify_line = adb.cat(path).strip("\n")
            if "\n" in verify_line or item.value not in verify_line.split():
                raise BootManagerError("verification failed after writing cmdline.txt")
            return

        # CONFIG_USER / BUILD_PROP: append-if-missing.
        path = REMOTE_PATHS[item.target]
        original = adb.cat(path)
        self._backup(item.target, original)
        prefix = original if (not original or original.endswith("\n")) else original + "\n"
        adb.write_text(path, prefix + item.value + "\n")
        verify = adb.cat(path)
        if not any(line.strip() == item.value for line in verify.splitlines()):
            raise BootManagerError(f"verification failed after writing {path}")

    def revert(self, adb: AdbClient, item: BootItem) -> None:
        if not adb.ready_to_write:
            raise BootManagerError("device must be connected, rooted, and remounted first")

        if item.target is BootTarget.SETTINGS:
            previous = self._read_setting_backup(item.setting_key)
            if previous is None:
                raise BootManagerError(f"no recorded backup for setting {item.setting_key}")
            adb.put_setting(item.setting_key, previous)
            return

        backup_path = self._latest_backup(item.target)
        if backup_path is None:
            raise BootManagerError(f"no backup found for {item.target.value} - nothing to revert to")
        content = backup_path.read_text(encoding="utf-8")
        adb.write_text(REMOTE_PATHS[item.target], content)

    # -- backups -------------------------------------------------------------

    def _backup(self, target: BootTarget, content: str) -> Path:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = self.backups_dir / f"{target.value}.{stamp}.bak"
        path.write_text(content, encoding="utf-8")
        return path

    def _latest_backup(self, target: BootTarget) -> Optional[Path]:
        candidates = sorted(self.backups_dir.glob(f"{target.value}.*.bak"))
        return candidates[-1] if candidates else None

    def _record_setting_backup(self, key: str, previous_value: str) -> None:
        data = {}
        if self._settings_backup_file.exists():
            data = json.loads(self._settings_backup_file.read_text(encoding="utf-8"))
        # Only record the first-ever previous value - repeated applies shouldn't
        # overwrite the original baseline the revert should restore.
        data.setdefault(key, previous_value)
        self._settings_backup_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _read_setting_backup(self, key: str) -> Optional[str]:
        if not self._settings_backup_file.exists():
            return None
        data = json.loads(self._settings_backup_file.read_text(encoding="utf-8"))
        return data.get(key)
