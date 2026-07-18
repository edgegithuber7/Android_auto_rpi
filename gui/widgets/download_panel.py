"""OS image download: open the KonstaKANG page for the selected board, or
fetch a pasted direct mirror URL in-app with a progress bar.

We deliberately don't scrape konstakang.com - its mirror links (SourceForge/
AndroidFileHost) aren't stable enough to parse reliably.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..downloader import DownloadWorker
from ..profiles import DeviceProfile


class DownloadPanel(QWidget):
    def __init__(self, profile: DeviceProfile, on_log: Callable[[str], None], parent=None):
        super().__init__(parent)
        self.profile = profile
        self.on_log = on_log
        self.worker: Optional[DownloadWorker] = None
        self._destination: Optional[str] = None

        box = QGroupBox("OS image download")
        layout = QVBoxLayout(box)

        self.page_label = QLabel()
        layout.addWidget(self.page_label)
        open_btn = QPushButton("Open download page in browser")
        open_btn.clicked.connect(self._open_page)
        layout.addWidget(open_btn)

        layout.addWidget(QLabel("Or paste a direct mirror link picked up from that page:"))
        direct_row = QHBoxLayout()
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://.../lineage-22.2-....zip")
        direct_row.addWidget(self.url_edit)
        self.browse_btn = QPushButton("Choose destination...")
        self.browse_btn.clicked.connect(self._choose_destination)
        direct_row.addWidget(self.browse_btn)
        layout.addLayout(direct_row)

        self.destination_label = QLabel("No destination chosen")
        layout.addWidget(self.destination_label)

        action_row = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self._start_download)
        action_row.addWidget(self.download_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_download)
        action_row.addWidget(self.cancel_btn)
        layout.addLayout(action_row)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)

        outer = QVBoxLayout(self)
        outer.addWidget(box)
        outer.setContentsMargins(0, 0, 0, 0)

        self.set_profile(profile)

    def set_profile(self, profile: DeviceProfile) -> None:
        self.profile = profile
        self.page_label.setText(f"{profile.label}: {profile.download_url}")

    def _open_page(self) -> None:
        QDesktopServices.openUrl(QUrl(self.profile.download_url))
        self.on_log(f"Opened {self.profile.download_url}")

    def _choose_destination(self) -> None:
        suggested = f"{self.profile.konstakang_slug}-lineage.zip"
        path, _ = QFileDialog.getSaveFileName(self, "Save image as", suggested)
        if path:
            self._destination = path
            self.destination_label.setText(path)

    def _start_download(self) -> None:
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Paste a direct download URL first.")
            return
        if not self._destination:
            QMessageBox.warning(self, "No destination", "Choose where to save the file first.")
            return
        if Path(self._destination).exists() and (
            QMessageBox.question(
                self, "File exists", "Destination file already exists - overwrite?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.worker = DownloadWorker(url, self._destination)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.on_log(f"Downloading {url} -> {self._destination}")
        self.worker.start()

    def _cancel_download(self) -> None:
        if self.worker:
            self.worker.cancel()

    def _on_progress(self, downloaded: int, total: int) -> None:
        if total:
            self.progress.setMaximum(total)
            self.progress.setValue(downloaded)
        else:
            self.progress.setMaximum(0)  # indeterminate - server didn't report a size

    def _on_finished(self, path: str) -> None:
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.on_log(f"Download complete: {path}")
        QMessageBox.information(self, "Download complete", path)

    def _on_failed(self, message: str) -> None:
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.on_log(f"Download failed: {message}")
        QMessageBox.critical(self, "Download failed", message)
