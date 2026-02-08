import sys
import time
from PySide6 import QtCore, QtGui, QtWidgets

from app.data.db import Database
from app.data.entry_repo import EntryRepo
from app.services.clipboard_service import ClipboardService
from app.services.grammar_service import GrammarService
from app.services.selection_service import SelectionService
from app.services.llm_service import LlmService
from app.ui.main_window import MainWindow


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)

    db = Database("data.sqlite")
    db.initialize()

    entry_repo = EntryRepo(db)

    selection_service = SelectionService()
    clipboard_service = ClipboardService(app.clipboard())
    grammar_service = GrammarService()
    llm_service = LlmService()

    window = MainWindow(
        entry_repo=entry_repo,
        selection_service=selection_service,
        clipboard_service=clipboard_service,
        grammar_service=grammar_service,
        llm_service=llm_service,
    )
    window.resize(1000, 600)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
