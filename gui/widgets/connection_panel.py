"""Device profile selector + ADB connection controls."""
from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..adb import AdbClient, AdbError
from ..profiles import PROFILES, DeviceProfile


class ConnectionPanel(QWidget):
    def __init__(
        self,
        adb: AdbClient,
        on_log: Callable[[str], None],
        on_profile_changed: Callable[[DeviceProfile], None],
        on_connection_changed: Callable[[], None],
        parent=None,
    ):
        super().__init__(parent)
        self.adb = adb
        self.on_log = on_log
        self.on_profile_changed = on_profile_changed
        self.on_connection_changed = on_connection_changed

        box = QGroupBox("Device")
        layout = QVBoxLayout(box)

        profile_row = QHBoxLayout()
        profile_row.addWidget(QLabel("Board:"))
        self.profile_combo = QComboBox()
        for profile in PROFILES:
            self.profile_combo.addItem(profile.label, userData=profile.name)
        self.profile_combo.currentIndexChanged.connect(self._profile_changed)
        profile_row.addWidget(self.profile_combo)
        layout.addLayout(profile_row)

        conn_row = QHBoxLayout()
        conn_row.addWidget(QLabel("IP:"))
        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("192.168.x.x")
        conn_row.addWidget(self.ip_edit)
        self.connect_btn = QPushButton("Connect (root + remount)")
        self.connect_btn.clicked.connect(self._connect)
        conn_row.addWidget(self.connect_btn)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._disconnect)
        conn_row.addWidget(self.disconnect_btn)
        self.reboot_btn = QPushButton("Reboot")
        self.reboot_btn.clicked.connect(self._reboot)
        conn_row.addWidget(self.reboot_btn)
        layout.addLayout(conn_row)

        self.status_label = QLabel("Disconnected")
        layout.addWidget(self.status_label)

        outer = QVBoxLayout(self)
        outer.addWidget(box)
        outer.setContentsMargins(0, 0, 0, 0)

        self._refresh_status()

    @property
    def selected_profile(self) -> DeviceProfile:
        name = self.profile_combo.currentData()
        return next(p for p in PROFILES if p.name == name)

    def _profile_changed(self, _index: int) -> None:
        self.on_profile_changed(self.selected_profile)

    def _connect(self) -> None:
        ip = self.ip_edit.text().strip()
        if not ip:
            QMessageBox.warning(self, "No IP address", "Enter the Pi's IP address first.")
            return
        try:
            self.adb.connect(ip)
            self.adb.root()
            self.adb.remount()
        except AdbError as exc:
            QMessageBox.critical(self, "Connection failed", str(exc))
        finally:
            self._refresh_status()
            self.on_connection_changed()

    def _disconnect(self) -> None:
        self.adb.disconnect()
        self._refresh_status()
        self.on_connection_changed()

    def _reboot(self) -> None:
        if not self.adb.device_ip:
            QMessageBox.warning(self, "Not connected", "Connect first.")
            return
        if (
            QMessageBox.question(self, "Reboot device", "Reboot the Pi now?")
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.adb.reboot()
        except AdbError as exc:
            QMessageBox.critical(self, "Reboot failed", str(exc))
        self._refresh_status()
        self.on_connection_changed()

    def _refresh_status(self) -> None:
        if not self.adb.device_ip:
            self.status_label.setText("Disconnected")
        elif self.adb.ready_to_write:
            self.status_label.setText(f"Connected to {self.adb.device_ip} - rooted + remounted")
        elif self.adb.rooted:
            self.status_label.setText(f"Connected to {self.adb.device_ip} - rooted, remount failed")
        else:
            self.status_label.setText(f"Connected to {self.adb.device_ip} - not rooted")
