"""Discovers the managed files in the repo (scripts/ + init/ + idc/).

Nothing here hardcodes today's two service names - drop a new
scripts/foo.sh + init/foo.rc pair into the repo and it shows up in the GUI
on the next scan, matching the existing tools/headunit.sh convention
(disable = rename .rc -> .rc.disabled).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List

from .adb import AdbClient

REMOTE_SCRIPT_DIR = "/system/bin"
REMOTE_INIT_DIR = "/system/etc/init"
REMOTE_IDC_DIR = "/system/usr/idc"


@dataclass
class ManagedService:
    """A scripts/<name>.sh + init/<name>.rc pair, installed and toggled together."""

    name: str
    script_path: Path
    rc_path: Path

    @property
    def remote_script(self) -> str:
        return f"{REMOTE_SCRIPT_DIR}/{self.name}.sh"

    @property
    def remote_rc(self) -> str:
        return f"{REMOTE_INIT_DIR}/{self.name}.rc"

    @property
    def remote_rc_disabled(self) -> str:
        return f"{self.remote_rc}.disabled"

    def status(self, adb: AdbClient) -> str:
        """One of: 'not installed' / 'enabled' / 'disabled'."""
        if adb.exists(self.remote_rc):
            return "enabled"
        if adb.exists(self.remote_rc_disabled):
            return "disabled"
        return "not installed"

    def is_running(self, adb: AdbClient) -> bool:
        result = adb.shell(f"ps -A | grep -c {self.name}")
        try:
            return int(result.stdout.strip() or "0") > 0
        except ValueError:
            return False

    def install(self, adb: AdbClient) -> None:
        """Push both files, enabled, leaving any existing disabled-state alone."""
        self.push_script(adb)
        if not adb.exists(self.remote_rc_disabled):
            self.push_rc(adb)

    def push_script(self, adb: AdbClient) -> None:
        adb.push(str(self.script_path), self.remote_script)
        adb.chmod(self.remote_script, "755")

    def push_rc(self, adb: AdbClient) -> None:
        """Push init/<name>.rc to whichever path is currently active on-device,
        so editing+pushing never silently re-enables a service you disabled."""
        target = self.remote_rc
        if adb.exists(self.remote_rc_disabled) and not adb.exists(self.remote_rc):
            target = self.remote_rc_disabled
        adb.push(str(self.rc_path), target)
        adb.chmod(target, "644")

    def enable(self, adb: AdbClient) -> None:
        if adb.exists(self.remote_rc_disabled):
            adb.rename(self.remote_rc_disabled, self.remote_rc)
        elif not adb.exists(self.remote_rc):
            self.install(adb)

    def disable(self, adb: AdbClient) -> None:
        adb.stop_service(self.name)
        if adb.exists(self.remote_rc):
            adb.rename(self.remote_rc, self.remote_rc_disabled)

    def uninstall(self, adb: AdbClient) -> None:
        adb.stop_service(self.name)
        adb.remove(self.remote_script)
        adb.remove(self.remote_rc)
        adb.remove(self.remote_rc_disabled)


@dataclass
class ManagedFile:
    """A standalone file (idc) - installed always, no enable/disable state."""

    name: str
    local_path: Path
    remote_dir: str
    mode: str = "644"

    @property
    def remote_path(self) -> str:
        return f"{self.remote_dir}/{self.local_path.name}"

    def install(self, adb: AdbClient) -> None:
        adb.push(str(self.local_path), self.remote_path)
        adb.chmod(self.remote_path, self.mode)

    def uninstall(self, adb: AdbClient) -> None:
        adb.remove(self.remote_path)

    def status(self, adb: AdbClient) -> str:
        return "installed" if adb.exists(self.remote_path) else "not installed"


def discover(repo_root: Path):
    """Scan scripts/ + init/ + idc/, pairing scripts with their init service by filename stem."""
    scripts_dir = repo_root / "scripts"
    init_dir = repo_root / "init"
    idc_dir = repo_root / "idc"

    services: List[ManagedService] = []
    if scripts_dir.is_dir() and init_dir.is_dir():
        rc_by_stem = {p.stem: p for p in init_dir.glob("*.rc")}
        for script in sorted(scripts_dir.glob("*.sh")):
            rc = rc_by_stem.get(script.stem)
            if rc is not None:
                services.append(ManagedService(name=script.stem, script_path=script, rc_path=rc))

    idc_files: List[ManagedFile] = []
    if idc_dir.is_dir():
        for idc in sorted(idc_dir.glob("*.idc")):
            idc_files.append(ManagedFile(name=idc.stem, local_path=idc, remote_dir=REMOTE_IDC_DIR))

    return services, idc_files


@dataclass
class EditableFile:
    """One tab's worth of content for the script editor."""

    label: str
    local_path: Path
    push: Callable[[AdbClient], None]
    status: Callable[[AdbClient], str]


def editable_files(services: List[ManagedService], idc_files: List[ManagedFile]) -> List[EditableFile]:
    files: List[EditableFile] = []
    for svc in services:
        files.append(
            EditableFile(
                label=f"scripts/{svc.name}.sh",
                local_path=svc.script_path,
                push=svc.push_script,
                status=svc.status,
            )
        )
        files.append(
            EditableFile(
                label=f"init/{svc.name}.rc",
                local_path=svc.rc_path,
                push=svc.push_rc,
                status=svc.status,
            )
        )
    for f in idc_files:
        files.append(
            EditableFile(
                label=f"idc/{f.local_path.name}",
                local_path=f.local_path,
                push=f.install,
                status=f.status,
            )
        )
    return files
