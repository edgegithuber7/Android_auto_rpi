"""Boot-partition / build.prop / settings tweaks, filtered by device profile.

Each row Apply goes through BootManager.preview_apply() first (confirmation
dialog) and BootManager.apply() always backs up the remote file/value before
writing - see boot_manager.py.
"""
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
from ..boot_manager import BootManager, BootManagerError
from ..profiles import BootItem, DeviceProfile


class BootItemRow(QWidget):
    def __init__(
        self,
        item: BootItem,
        adb: AdbClient,
        manager: BootManager,
        on_log: Callable[[str], None],
    ):
        super().__init__()
        self.item = item
        self.adb = adb
        self.manager = manager
        self.on_log = on_log

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = f"{item.description} ({item.value})"
        if not item.required:
            label += " [optional]"
        text_label = QLabel(label)
        text_label.setWordWrap(True)
        layout.addWidget(text_label, stretch=3)
        self.status_label = QLabel("unknown")
        layout.addWidget(self.status_label, stretch=1)

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self._apply)
        layout.addWidget(self.apply_btn)

        self.revert_btn = QPushButton("Revert")
        self.revert_btn.clicked.connect(self._revert)
        layout.addWidget(self.revert_btn)

    def refresh(self) -> None:
        if not self.adb.device_ip:
            self.status_label.setText("unknown (not connected)")
            return
        try:
            applied = self.manager.is_applied(self.adb, self.item)
        except AdbError as exc:
            self.status_label.setText(f"error: {exc}")
            return
        self.status_label.setText("applied" if applied else "not applied")

    def _require_writable(self) -> bool:
        if not self.adb.ready_to_write:
            QMessageBox.warning(self, "Not connected", "Connect, root, and remount first.")
            return False
        return True

    def _apply(self) -> None:
        if not self._require_writable():
            return
        try:
            preview = self.manager.preview_apply(self.adb, self.item)
        except AdbError as exc:
            QMessageBox.critical(self, "Could not preview change", str(exc))
            return
        if preview.already_applied:
            QMessageBox.information(self, "Already applied", preview.summary)
            self.refresh()
            return
        if (
            QMessageBox.question(self, "Confirm change", preview.summary)
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.manager.apply(self.adb, self.item)
            self.on_log(f"Applied {self.item.key}")
        except (AdbError, BootManagerError) as exc:
            QMessageBox.critical(self, "Apply failed", str(exc))
        self.refresh()

    def _revert(self) -> None:
        if not self._require_writable():
            return
        if (
            QMessageBox.question(
                self, "Revert change", f"Restore the pre-change value for '{self.item.key}'?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            self.manager.revert(self.adb, self.item)
            self.on_log(f"Reverted {self.item.key}")
        except (AdbError, BootManagerError) as exc:
            QMessageBox.critical(self, "Revert failed", str(exc))
        self.refresh()


class BootPanel(QWidget):
    def __init__(
        self,
        profile: DeviceProfile,
        adb: AdbClient,
        manager: BootManager,
        on_log: Callable[[str], None],
        parent=None,
    ):
        super().__init__(parent)
        self.adb = adb
        self.manager = manager
        self.on_log = on_log
        self.rows: List[BootItemRow] = []

        self.box = QGroupBox("Boot / build.prop / settings changes")
        self.items_layout = QVBoxLayout(self.box)

        refresh_btn = QPushButton("Refresh status")
        refresh_btn.clicked.connect(self.refresh)

        outer = QVBoxLayout(self)
        outer.addWidget(self.box)
        outer.addWidget(refresh_btn)
        outer.setContentsMargins(0, 0, 0, 0)

        self.set_profile(profile)

    def set_profile(self, profile: DeviceProfile) -> None:
        for row in self.rows:
            self.items_layout.removeWidget(row)
            row.setParent(None)
        self.rows.clear()
        self.box.setTitle(f"Boot / build.prop / settings changes - {profile.label}")
        for item in profile.boot_items():
            row = BootItemRow(item, self.adb, self.manager, self.on_log)
            self.rows.append(row)
            self.items_layout.addWidget(row)
        self.refresh()

    def refresh(self) -> None:
        for row in self.rows:
            row.refresh()
