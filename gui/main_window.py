"""Main application window - assembles all panels."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .adb import AdbClient, AdbError
from .boot_manager import BootManager
from .repo_model import discover, editable_files
from .widgets.boot_panel import BootPanel
from .widgets.connection_panel import ConnectionPanel
from .widgets.download_panel import DownloadPanel
from .widgets.editor_tabs import EditorTabs
from .widgets.log_panel import LogPanel
from .widgets.service_panel import ServicePanel

REPO_ROOT = Path(__file__).resolve().parent.parent


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pi Head Unit Manager")
        self.resize(1150, 820)

        self.log_panel = LogPanel()
        self.adb = AdbClient(log=self.log_panel.log)

        self.services, self.idc_files = discover(REPO_ROOT)
        self.boot_manager = BootManager(REPO_ROOT / "gui" / "backups")

        self.connection_panel = ConnectionPanel(
            self.adb, self.log_panel.log, self._profile_changed, self._connection_changed
        )
        profile = self.connection_panel.selected_profile

        self.service_panel = ServicePanel(self.services, self.adb, self.log_panel.log)
        self.boot_panel = BootPanel(profile, self.adb, self.boot_manager, self.log_panel.log)
        self.download_panel = DownloadPanel(profile, self.log_panel.log)

        files = editable_files(self.services, self.idc_files)
        self.editor_tabs = EditorTabs(files, self.adb, self.log_panel.log)

        left_tabs = QTabWidget()
        left_tabs.addTab(self._scrollable(self.connection_panel), "Connection")
        left_tabs.addTab(self._scrollable(self.service_panel), "Services")
        left_tabs.addTab(self._scrollable(self.boot_panel), "Boot changes")
        left_tabs.addTab(self._scrollable(self.download_panel), "Download")

        install_row = QWidget()
        install_layout = QHBoxLayout(install_row)
        install_all_btn = QPushButton("Install all")
        install_all_btn.clicked.connect(self._install_all)
        install_layout.addWidget(install_all_btn)
        uninstall_all_btn = QPushButton("Uninstall all")
        uninstall_all_btn.clicked.connect(self._uninstall_all)
        install_layout.addWidget(uninstall_all_btn)

        left_column = QWidget()
        left_col_layout = QVBoxLayout(left_column)
        left_col_layout.addWidget(left_tabs)
        left_col_layout.addWidget(install_row)

        top_split = QSplitter(Qt.Orientation.Horizontal)
        top_split.addWidget(left_column)
        top_split.addWidget(self.editor_tabs)
        top_split.setStretchFactor(0, 2)
        top_split.setStretchFactor(1, 3)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(top_split)
        splitter.addWidget(self.log_panel)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        if not self.services and not self.idc_files:
            self.log_panel.log(
                "No managed scripts/init/idc files found under the repo root - "
                "nothing to show in Services / Editor."
            )

    @staticmethod
    def _scrollable(widget: QWidget) -> QScrollArea:
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(widget)
        return area

    def _profile_changed(self, profile) -> None:
        self.boot_panel.set_profile(profile)
        self.download_panel.set_profile(profile)

    def _connection_changed(self) -> None:
        self.service_panel.refresh()
        self.boot_panel.refresh()

    def _install_all(self) -> None:
        if not self.adb.ready_to_write:
            QMessageBox.warning(self, "Not connected", "Connect, root, and remount first.")
            return
        try:
            for service in self.services:
                service.install(self.adb)
            for idc in self.idc_files:
                idc.install(self.adb)
        except AdbError as exc:
            QMessageBox.critical(self, "Install failed", str(exc))
            self.service_panel.refresh()
            return
        self.service_panel.refresh()
        self.log_panel.log("Install all: done. Reboot to activate.")
        QMessageBox.information(
            self, "Installed", "All managed files pushed. Reboot the Pi to activate."
        )

    def _uninstall_all(self) -> None:
        if not self.adb.ready_to_write:
            QMessageBox.warning(self, "Not connected", "Connect, root, and remount first.")
            return
        if (
            QMessageBox.question(
                self,
                "Uninstall all",
                "Remove every managed script/service/idc file from the device?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        try:
            for service in self.services:
                service.uninstall(self.adb)
            for idc in self.idc_files:
                idc.uninstall(self.adb)
        except AdbError as exc:
            QMessageBox.critical(self, "Uninstall failed", str(exc))
            self.service_panel.refresh()
            return
        self.service_panel.refresh()
        self.log_panel.log("Uninstall all: done.")
