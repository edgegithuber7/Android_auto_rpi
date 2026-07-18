"""Read-only log console - every adb/download action gets appended here."""
from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QPlainTextEdit


class _LogSignal(QObject):
    message = pyqtSignal(str)


class LogPanel(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self._signal = _LogSignal()
        self._signal.message.connect(self._append)

    def log(self, message: str) -> None:
        """Safe to call from any thread - routes through a Qt signal onto the GUI thread."""
        self._signal.message.emit(message)

    def _append(self, message: str) -> None:
        self.appendPlainText(message)
