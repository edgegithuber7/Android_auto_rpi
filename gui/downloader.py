"""Direct-download worker.

Fetches a user-supplied URL (e.g. a KonstaKANG mirror link picked from the
browser) to disk with a progress bar, resuming a partial ".part" file if the
server honours HTTP Range requests. Uses stdlib urllib only - no extra
dependency for what is, in the common case, one big file.
"""
from __future__ import annotations

import os
import urllib.error
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

CHUNK_SIZE = 256 * 1024


class DownloadWorker(QThread):
    progress = pyqtSignal(int, int)  # bytes_downloaded, total_bytes (0 if unknown)
    finished_ok = pyqtSignal(str)    # final file path
    failed = pyqtSignal(str)         # error message

    def __init__(self, url: str, destination: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.destination = destination
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        part_path = self.destination + ".part"
        resume_from = os.path.getsize(part_path) if os.path.exists(part_path) else 0

        request = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
        if resume_from:
            request.add_header("Range", f"bytes={resume_from}-")

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                accepted_range = response.status == 206
                if resume_from and not accepted_range:
                    resume_from = 0  # server ignored Range - must restart from scratch

                content_length = response.headers.get("Content-Length")
                total = int(content_length) if content_length else 0
                if accepted_range:
                    content_range = response.headers.get("Content-Range", "")
                    if "/" in content_range:
                        try:
                            total = int(content_range.rsplit("/", 1)[-1])
                        except ValueError:
                            pass

                mode = "ab" if (resume_from and accepted_range) else "wb"
                downloaded = resume_from if mode == "ab" else 0
                self.progress.emit(downloaded, total)

                with open(part_path, mode) as fh:
                    while not self._cancelled:
                        chunk = response.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        fh.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            self.failed.emit(str(exc))
            return

        if self._cancelled:
            self.failed.emit("Download cancelled - partial file kept on disk for resume.")
            return

        os.replace(part_path, self.destination)
        self.finished_ok.emit(self.destination)
