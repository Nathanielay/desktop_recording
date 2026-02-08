from PySide6 import QtCore, QtGui


class ClipboardService(QtCore.QObject):
    text_copied = QtCore.Signal(str)

    def __init__(self, clipboard: QtGui.QClipboard) -> None:
        super().__init__()
        self._clipboard = clipboard
        self._clipboard.dataChanged.connect(self._on_change)

    def get_text(self) -> str:
        return self._clipboard.text().strip()

    def _on_change(self) -> None:
        text = self.get_text()
        if text:
            self.text_copied.emit(text)
