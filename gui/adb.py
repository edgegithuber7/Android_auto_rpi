"""Thin, logged wrapper around the `adb` command-line tool.

Reimplements the connect/root/remount/push/pull/enable/disable flow that
tools/headunit.sh does in bash, natively in Python so the GUI has no
bash/WSL dependency. Every adb invocation is reported to an optional log
callback so the app's log panel can show exactly what ran.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Optional

LogFn = Callable[[str], None]


class AdbError(RuntimeError):
    """Raised when an adb invocation fails, or adb itself can't be found."""


@dataclass
class CommandResult:
    args: list
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def find_adb() -> str:
    path = shutil.which("adb")
    if not path:
        raise AdbError(
            "adb not found on PATH. Install Android platform-tools and make "
            "sure 'adb' is reachable from a terminal."
        )
    return path


class AdbClient:
    """Runs adb commands via subprocess; tracks connect/root/remount state."""

    def __init__(self, log: Optional[LogFn] = None, timeout: float = 30.0):
        # Resolved lazily (not here) so building the GUI doesn't crash on a
        # machine that hasn't installed platform-tools yet - the error only
        # surfaces when something actually tries to run adb.
        self._adb_path: Optional[str] = None
        self._log = log or (lambda _msg: None)
        self.timeout = timeout
        self.device_ip: Optional[str] = None
        self.rooted = False
        self.remounted = False

    # -- low level -------------------------------------------------------

    def _run(self, args: list, timeout: Optional[float] = None) -> CommandResult:
        if self._adb_path is None:
            self._adb_path = find_adb()
        full = [self._adb_path, *args]
        self._log(f"$ {' '.join(full)}")
        try:
            proc = subprocess.run(
                full,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
            )
        except FileNotFoundError as exc:
            raise AdbError(f"adb executable disappeared: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise AdbError(f"adb command timed out: {' '.join(full)}") from exc

        out = proc.stdout.strip()
        err = proc.stderr.strip()
        if out:
            self._log(out)
        if err:
            self._log(err)
        return CommandResult(full, proc.returncode, out, err)

    def shell(self, command: str, timeout: Optional[float] = None) -> CommandResult:
        """Run a single command string through `adb shell`."""
        return self._run(["shell", command], timeout=timeout)

    # -- connection lifecycle --------------------------------------------

    def connect(self, ip: str, port: int = 5555) -> None:
        target = f"{ip}:{port}"
        result = self._run(["connect", target])
        low = result.stdout.lower()
        if not result.ok or "unable to connect" in low or "failed" in low:
            raise AdbError(f"adb connect failed: {result.stdout or result.stderr}")
        self.device_ip = ip
        self.rooted = False
        self.remounted = False

    def root(self) -> None:
        if not self.device_ip:
            raise AdbError("not connected - call connect() first")
        self._run(["root"])
        # adbd restarts after `adb root` and briefly drops the connection.
        time.sleep(2)
        self._run(["connect", f"{self.device_ip}:5555"])
        who = self.whoami()
        self.rooted = who == "root"
        if not self.rooted:
            raise AdbError(f"adb root did not elevate (whoami={who!r})")

    def remount(self) -> None:
        if not self.rooted:
            raise AdbError("must be root before remount() - call root() first")
        result = self._run(["remount"])
        self.remounted = result.ok
        if not self.remounted:
            raise AdbError(f"adb remount failed: {result.stdout or result.stderr}")

    def disconnect(self) -> None:
        if self.device_ip:
            self._run(["disconnect", f"{self.device_ip}:5555"])
        self.device_ip = None
        self.rooted = False
        self.remounted = False

    def reboot(self) -> None:
        self._run(["reboot"])
        self.rooted = False
        self.remounted = False

    def is_connected(self) -> bool:
        if not self.device_ip:
            return False
        result = self._run(["get-state"], timeout=5)
        return result.ok and result.stdout.strip() == "device"

    def whoami(self) -> str:
        return self.shell("whoami").stdout.strip()

    @property
    def ready_to_write(self) -> bool:
        """True once connected, rooted, and remounted - the gate for any on-device write."""
        return bool(self.device_ip) and self.rooted and self.remounted

    # -- file transfer -----------------------------------------------------

    def push(self, local: str, remote: str) -> None:
        result = self._run(["push", local, remote])
        if not result.ok:
            raise AdbError(f"push failed ({local} -> {remote}): {result.stderr or result.stdout}")

    def pull(self, remote: str, local: str) -> None:
        result = self._run(["pull", remote, local])
        if not result.ok:
            raise AdbError(f"pull failed ({remote} -> {local}): {result.stderr or result.stdout}")

    def chmod(self, remote: str, mode: str) -> None:
        result = self.shell(f"chmod {mode} '{remote}'")
        if not result.ok:
            raise AdbError(f"chmod {mode} {remote} failed: {result.stderr or result.stdout}")

    def cat(self, remote: str) -> str:
        """Read a remote file's contents (empty string if it doesn't exist)."""
        result = self.shell(f"cat '{remote}' 2>/dev/null")
        return result.stdout

    def exists(self, remote: str) -> bool:
        result = self.shell(f"ls '{remote}' 2>/dev/null")
        return result.ok and bool(result.stdout.strip())

    def write_text(self, remote: str, content: str) -> None:
        """Overwrite a remote text file whole, via a heredoc (no partial writes)."""
        marker = "__ADB_GUI_EOF__"
        body = content if content.endswith("\n") else content + "\n"
        cmd = f"cat > '{remote}' << '{marker}'\n{body}{marker}\n"
        result = self.shell(cmd, timeout=15)
        if not result.ok:
            raise AdbError(f"writing {remote} failed: {result.stderr or result.stdout}")

    def rename(self, src: str, dst: str) -> None:
        result = self.shell(f"mv '{src}' '{dst}'")
        if not result.ok:
            raise AdbError(f"rename {src} -> {dst} failed: {result.stderr or result.stdout}")

    def remove(self, remote: str) -> None:
        # rm of a nonexistent file is not an error - keep uninstall idempotent.
        self.shell(f"rm -f '{remote}'")

    def stop_service(self, name: str) -> None:
        self.shell(f"stop {name} 2>/dev/null")

    def get_setting(self, key: str) -> str:
        return self.shell(f"settings get global {key}").stdout.strip()

    def put_setting(self, key: str, value: str) -> None:
        result = self.shell(f"settings put global {key} {value}")
        if not result.ok:
            raise AdbError(f"settings put global {key} {value} failed: {result.stderr}")
