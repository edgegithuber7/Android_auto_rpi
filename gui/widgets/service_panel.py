"""Per-service status / enable / disable / install / uninstall controls."""
from __future__ import annotations

from typing import Callable, List

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..adb import AdbClient, AdbError
from ..repo_model import ManagedService


class ServiceRow(QWidget):
    def __init__(
        self,
        service: ManagedService,
        adb: AdbClient,
        on_log: Callable[[str], None],
    ):
        super().__init__()
        self.service = service
        self.adb = adb
        self.on_log = on_log

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(service.name), stretch=1)
        self.status_label = QLabel("unknown")
        layout.addWidget(self.status_label, stretch=1)

        self.toggle_btn = QPushButton("Enable / Disable")
        self.toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self.toggle_btn)

        self.install_btn = QPushButton("(Re)install")
        self.install_btn.clicked.connect(self._install)
        layout.addWidget(self.install_btn)

        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.clicked.connect(self._uninstall)
        layout.addWidget(self.uninstall_btn)

    def refresh(self) -> None:
        if not self.adb.device_ip:
            self.status_label.setText("unknown (not connected)")
            return
        try:
            status = self.service.status(self.adb)
            running = self.service.is_running(self.adb)
        except AdbError as exc:
            self.status_label.setText(f"error: {exc}")
            return
        self.status_label.setText(f"{status}{' - running' if running else ''}")

    def _require_writable(self) -> bool:
        if not self.adb.ready_to_write:
            QMessageBox.warning(self, "Not connected", "Connect, root, and remount first.")
            return False
        return True

    def _toggle(self) -> None:
        if not self._require_writable():
            return
        try:
            status = self.service.status(self.adb)
            if status == "enabled":
                self.service.disable(self.adb)
                self.on_log(f"Disabled {self.service.name}")
            else:
                self.service.enable(self.adb)
                self.on_log(f"Enabled {self.service.name}")
        except AdbError as exc:
            QMessageBox.critical(self, "Action failed", str(exc))
        self.refresh()

    def _install(self) -> None:
        if not self._require_writable():
            return
        try:
            self.service.install(self.adb)
            self.on_log(f"Installed {self.service.name}")
        except AdbError as exc:
            QMessageBox.critical(self, "Install failed", str(exc))
        self.refresh()

    def _uninstall(self) -> None:
        if not self._require_writable():
            return
        if (
            QMessageBox.question(
                self, "Uninstall service", f"Remove {self.service.name} from the device?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.service.uninstall(self.adb)
            self.on_log(f"Uninstalled {self.service.name}")
        except AdbError as exc:
            QMessageBox.critical(self, "Uninstall failed", str(exc))
        self.refresh()


class ServicePanel(QWidget):
    def __init__(
        self,
        services: List[ManagedService],
        adb: AdbClient,
        on_log: Callable[[str], None],
        parent=None,
    ):
        super().__init__(parent)
        self.adb = adb
        self.on_log = on_log
        self.rows: List[ServiceRow] = []

        box = QGroupBox("Services (scripts/*.sh + init/*.rc pairs)")
        layout = QVBoxLayout(box)
        header = QHBoxLayout()
        header.addWidget(QLabel("Name"), stretch=1)
        header.addWidget(QLabel("Status"), stretch=1)
        layout.addLayout(header)

        for service in services:
            row = ServiceRow(service, adb, on_log)
            self.rows.append(row)
            layout.addWidget(row)

        refresh_btn = QPushButton("Refresh status")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        outer = QVBoxLayout(self)
        outer.addWidget(box)
        outer.setContentsMargins(0, 0, 0, 0)

    def refresh(self) -> None:
        for row in self.rows:
            row.refresh()
