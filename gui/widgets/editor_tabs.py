"""Tabbed editor for every managed script/init/idc file.

Save writes the local repo file; Push sends just that file to the device.
The two are always separate actions - editing never silently touches the
device, matching the repo's local-file-is-source-of-truth convention.
"""
from __future__ import annotations

from typing import Callable, List

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..adb import AdbClient, AdbError
from ..repo_model import EditableFile


class EditorTab(QWidget):
    def __init__(
        self,
        file: EditableFile,
        adb: AdbClient,
        on_log: Callable[[str], None],
        on_dirty_changed: Callable[["EditorTab"], None],
    ):
        super().__init__()
        self.file = file
        self.adb = adb
        self.on_log = on_log
        self.on_dirty_changed = on_dirty_changed
        self._dirty = False

        layout = QVBoxLayout(self)
        self.editor = QPlainTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setPlainText(file.local_path.read_text(encoding="utf-8"))
        self.editor.textChanged.connect(self._mark_dirty)
        layout.addWidget(self.editor)

        button_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save)
        button_row.addWidget(self.save_btn)
        self.push_btn = QPushButton("Push to device")
        self.push_btn.clicked.connect(self.push)
        button_row.addWidget(self.push_btn)
        self.status_label = QLabel("")
        button_row.addWidget(self.status_label, stretch=1)
        layout.addLayout(button_row)

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.on_dirty_changed(self)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def save(self) -> None:
        text = self.editor.toPlainText()
        self.file.local_path.write_text(text, encoding="utf-8", newline="\n")
        self._dirty = False
        self.on_dirty_changed(self)
        self.on_log(f"Saved {self.file.label}")

    def push(self) -> None:
        if self.dirty and (
            QMessageBox.question(
                self, "Unsaved changes", "Save local changes before pushing?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            self.save()
        if not self.adb.ready_to_write:
            QMessageBox.warning(self, "Not connected", "Connect, root, and remount first.")
            return
        try:
            self.file.push(self.adb)
        except AdbError as exc:
            QMessageBox.critical(self, "Push failed", str(exc))
            return
        self.on_log(f"Pushed {self.file.label} to device")
        QMessageBox.information(
            self, "Pushed", f"{self.file.label} pushed. Reboot to apply if it's a boot service."
        )


class EditorTabs(QTabWidget):
    def __init__(
        self,
        files: List[EditableFile],
        adb: AdbClient,
        on_log: Callable[[str], None],
        parent=None,
    ):
        super().__init__(parent)
        self.tabs: List[EditorTab] = []
        for file in files:
            tab = EditorTab(file, adb, on_log, self._dirty_changed)
            self.tabs.append(tab)
            self.addTab(tab, file.label)

    def _dirty_changed(self, tab: EditorTab) -> None:
        index = self.indexOf(tab)
        if index < 0:
            return
        base = tab.file.label
        self.setTabText(index, f"{base} *" if tab.dirty else base)
