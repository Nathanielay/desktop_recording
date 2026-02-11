import json
from PySide6 import QtCore, QtGui, QtWidgets

from app.data.entry_repo import EntryRepo
from app.services.clipboard_service import ClipboardService
from app.services.selection_service import SelectionService
from app.services.grammar_service import GrammarService
from app.services.llm_service import LlmService
from app.utils.text_detect import detect_entry_type, is_english
from app.utils.auto_tags import build_auto_tags


class _LlmWorker(QtCore.QObject):
    finished = QtCore.Signal(str, str, dict)
    failed = QtCore.Signal(str)

    def __init__(self, llm_service: LlmService, text: str, entry_type: str) -> None:
        super().__init__()
        self._llm_service = llm_service
        self._text = text
        self._entry_type = entry_type

    def run(self) -> None:
        try:
            result = self._llm_service.enrich(self._text, self._entry_type)
            self.finished.emit(self._text, self._entry_type, result)
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(
        self,
        entry_repo: EntryRepo,
        selection_service: SelectionService,
        clipboard_service: ClipboardService,
        grammar_service: GrammarService,
        llm_service: LlmService,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Desktop Capture + Grammar Analysis (MVP)")
        self._entry_repo = entry_repo
        self._selection_service = selection_service
        self._clipboard_service = clipboard_service
        self._grammar_service = grammar_service
        self._llm_service = llm_service

        self._setup_ui()
        self._refresh_entries()
        self._current_entry = None
        self._current_related_ids = []

        self._clipboard_service.text_copied.connect(self._on_clipboard_change)

    def _setup_ui(self) -> None:
        root = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(root)

        self._entry_tabs = QtWidgets.QTabWidget()
        self._list_word = QtWidgets.QListWidget()
        self._list_phrase = QtWidgets.QListWidget()
        self._list_article = QtWidgets.QListWidget()
        self._list_word.currentItemChanged.connect(self._on_entry_selected)
        self._list_phrase.currentItemChanged.connect(self._on_entry_selected)
        self._list_article.currentItemChanged.connect(self._on_entry_selected)
        self._entry_tabs.addTab(self._list_word, "Word")
        self._entry_tabs.addTab(self._list_phrase, "Phrase")
        self._entry_tabs.addTab(self._list_article, "Article")
        layout.addWidget(self._entry_tabs, 2)

        self._right_tabs = QtWidgets.QTabWidget()
        self._entry_tab_index = self._right_tabs.addTab(self._build_entry_tab(), "Entry")
        layout.addWidget(self._right_tabs, 3)

        self.setCentralWidget(root)

        capture_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Shift+C"), self)
        capture_shortcut.activated.connect(self._capture_from_selection)

        self._llm_thread = None
        self._llm_worker = None

    def _build_entry_tab(self) -> QtWidgets.QWidget:
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)

        self._capture_button = QtWidgets.QPushButton("Capture Selection")
        self._capture_button.clicked.connect(self._capture_from_selection)

        self._status_label = QtWidgets.QLabel("Idle")
        self._status_label.setWordWrap(True)

        self._detail_text = QtWidgets.QTextEdit()
        self._detail_text.setReadOnly(True)

        self._structure_legend = QtWidgets.QLabel(
            "Structure Highlight: Subject (yellow), Verb (red), Object (green), Clause (blue)"
        )
        self._structure_legend.setWordWrap(True)
        self._structure_view = QtWidgets.QTextEdit()
        self._structure_view.setReadOnly(True)
        self._structure_view.setPlaceholderText("Phrase/Article structure will appear here.")
        self._structure_legend.hide()
        self._structure_view.hide()

        self._tags_input = QtWidgets.QLineEdit()
        self._tags_input.setPlaceholderText("Tags (comma separated)")
        save_tags_button = QtWidgets.QPushButton("Save Tags")
        save_tags_button.clicked.connect(self._save_tags)

        self._related_search = QtWidgets.QLineEdit()
        self._related_search.setPlaceholderText("Search words to relate")
        self._related_search.textChanged.connect(self._update_related_options)
        self._related_combo = QtWidgets.QComboBox()
        self._related_combo.setEditable(False)
        add_related_button = QtWidgets.QPushButton("Add Related Word")
        add_related_button.clicked.connect(self._save_related)
        self._related_input = QtWidgets.QLineEdit()
        self._related_input.setPlaceholderText("Related words (auto-filled)")
        self._related_input.setReadOnly(True)

        layout.addWidget(self._capture_button)
        layout.addWidget(self._status_label)
        layout.addWidget(self._detail_text, 1)
        layout.addWidget(self._structure_legend)
        layout.addWidget(self._structure_view, 1)
        layout.addWidget(self._tags_input)
        layout.addWidget(save_tags_button)
        layout.addWidget(self._related_search)
        layout.addWidget(self._related_combo)
        layout.addWidget(add_related_button)
        layout.addWidget(self._related_input)
        return widget

    def _refresh_entries(self) -> None:
        self._list_word.clear()
        self._list_phrase.clear()
        self._list_article.clear()
        for entry in self._entry_repo.list_entries():
            item = QtWidgets.QListWidgetItem(entry["text"])
            item.setData(QtCore.Qt.ItemDataRole.UserRole, entry)
            entry_type = entry.get("entry_type")
            if entry_type == "word":
                self._list_word.addItem(item)
            elif entry_type == "phrase":
                self._list_phrase.addItem(item)
            else:
                self._list_article.addItem(item)

    def _on_entry_selected(self, current: QtWidgets.QListWidgetItem) -> None:
        if not current:
            return
        entry = current.data(QtCore.Qt.ItemDataRole.UserRole)
        self._current_entry = entry
        detail = self._format_detail(entry)
        self._detail_text.setPlainText(detail)
        tags_value = entry.get("tags", "")
        try:
            tags_list = json.loads(tags_value) if tags_value else []
            tags_text = ", ".join(str(item) for item in tags_list)
        except Exception:
            tags_text = tags_value
        self._tags_input.setText(tags_text)
        related_value = entry.get("related_entry_ids", "")
        related_list = self._parse_related_ids(related_value)
        self._current_related_ids = related_list
        related_text = self._format_related_terms(related_list)
        self._related_input.setText(related_text)
        self._related_search.clear()
        self._update_related_options("")
        self._update_structure_view(entry)

    def _on_clipboard_change(self, text: str) -> None:
        self._status_label.setText(f"Clipboard updated: {text[:80]}")

    def _capture_from_selection(self) -> None:
        text = self._selection_service.get_selected_text()
        if not text:
            text = self._clipboard_service.get_text()
        if not text:
            self._status_label.setText("No text captured.")
            return
        if not is_english(text):
            self._status_label.setText("Captured text is not English enough to store.")
            return

        entry_type = detect_entry_type(text)
        self._status_label.setText("Calling LLM for enrichment...")
        self._capture_button.setEnabled(False)
        if self._llm_thread and self._llm_thread.isRunning():
            self._status_label.setText("LLM request already running.")
            self._capture_button.setEnabled(True)
            return
        worker = _LlmWorker(self._llm_service, text, entry_type)
        thread = QtCore.QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_llm_finished)
        worker.failed.connect(self._on_llm_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(thread.quit)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_llm_thread_finished)
        self._llm_worker = worker
        self._llm_thread = thread
        thread.start()

    def _on_llm_finished(self, text: str, entry_type: str, enrich: dict) -> None:
        def _to_text(value) -> str:
            if value is None:
                return ""
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=True)
            return str(value)

        auto_tags = []
        if entry_type == "word":
            existing_words = self._entry_repo.list_word_entries()
            auto_tags = build_auto_tags(
                text,
                _to_text(enrich.get("translation", "")),
                existing_words,
            )

        entry_payload = {
            "entry_type": entry_type,
            "text": text,
            "translation": _to_text(enrich.get("translation", "")),
            "phonetic_us": _to_text(enrich.get("phonetic_us", "")),
            "phonetic_uk": _to_text(enrich.get("phonetic_uk", "")),
            "definition": _to_text(enrich.get("definition", "")),
            "part_of_speech": _to_text(enrich.get("part_of_speech", "")),
            "ipa": _to_text(enrich.get("ipa", "")),
            "word_roots": json.dumps(enrich.get("word_roots", []), ensure_ascii=True),
            "tense_form": json.dumps(enrich.get("tense_form", []), ensure_ascii=True),
            "common_meanings": json.dumps(enrich.get("common_meanings", []), ensure_ascii=True),
            "related_entry_ids": json.dumps(enrich.get("related_terms", []), ensure_ascii=True),
            "tags": json.dumps(auto_tags, ensure_ascii=True),
            "grammar_notes": _to_text(enrich.get("grammar_notes", "")),
            "structure_breakdown": json.dumps(enrich.get("structure_breakdown", []), ensure_ascii=True),
            "key_terms": json.dumps(enrich.get("key_terms", []), ensure_ascii=True),
            "raw_llm": _to_text(enrich.get("raw_llm", "")),
        }
        entry_id, created = self._entry_repo.add_entry(entry_payload)
        if created:
            self._status_label.setText(f"Saved entry #{entry_id} ({entry_type}).")
        else:
            self._status_label.setText(f"Duplicate entry #{entry_id} ({entry_type}).")
        self._capture_button.setEnabled(True)
        self._refresh_entries()
        self._tags_input.clear()
        self._related_input.clear()
        self._related_search.clear()
        self._related_combo.clear()

    def _on_llm_failed(self, message: str) -> None:
        self._status_label.setText(f"LLM failed: {message}")
        self._capture_button.setEnabled(True)

    def _on_llm_thread_finished(self) -> None:
        self._llm_worker = None
        self._llm_thread = None

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._llm_thread and self._llm_thread.isRunning():
            self._llm_thread.quit()
            self._llm_thread.wait(2000)
        super().closeEvent(event)

    def _format_detail(self, entry: dict) -> str:
        entry_type = entry.get("entry_type")
        def _json_to_text(value: str) -> str:
            try:
                parsed = json.loads(value) if value else []
                if isinstance(parsed, list):
                    return ", ".join(str(item) for item in parsed)
                return str(parsed)
            except Exception:
                return value

        def _format_ipa(value: str) -> str:
            if not value:
                return ""
            lower = value.lower()
            if "uk:" in lower and "us:" in lower:
                try:
                    parts = value.replace("UK:", "UK:").replace("US:", "US:").split(";")
                    uk = parts[0].split("UK:")[1].strip()
                    us = parts[1].split("US:")[1].strip()
                    return f"英 [{uk.strip('/')}]\n美 [{us.strip('/')}]"
                except Exception:
                    return value
            return value

        lines = [
            f"Type: {entry_type}",
            f"Text: {entry.get('text','')}",
            f"Translation: {entry.get('translation','')}",
        ]
        if entry_type == "word":
            lines.extend(
                [
                    f"Part of Speech: {entry.get('part_of_speech','')}",
                    f"IPA: {_format_ipa(entry.get('ipa',''))}",
                    f"Phonetic US: {entry.get('phonetic_us','')}",
                    f"Phonetic UK: {entry.get('phonetic_uk','')}",
                    f"Roots: {_json_to_text(entry.get('word_roots',''))}",
                    f"Tense/Form: {_json_to_text(entry.get('tense_form',''))}",
                    f"Common Meanings: {_json_to_text(entry.get('common_meanings',''))}",
                    f"Related Terms: {self._format_related_terms(self._parse_related_ids(entry.get('related_entry_ids','')))}",
                    f"Tags: {_json_to_text(entry.get('tags',''))}",
                    f"Definition: {entry.get('definition','')}",
                ]
            )
        else:
            lines.extend(
                [
                    f"Structure Breakdown: {_json_to_text(entry.get('structure_breakdown',''))}",
                    f"Grammar Notes: {entry.get('grammar_notes','')}",
                    f"Key Terms: {_json_to_text(entry.get('key_terms',''))}",
                ]
            )
        return "\n".join(lines)

    def _update_structure_view(self, entry: dict) -> None:
        entry_type = entry.get("entry_type")
        if entry_type not in {"phrase", "article"}:
            self._structure_legend.hide()
            self._structure_view.hide()
            self._structure_view.clear()
            return
        analysis = self._grammar_service.analyze(entry.get("text", ""))
        highlighted_html = analysis.get("highlighted_html")
        if highlighted_html:
            self._structure_view.setHtml(highlighted_html)
        else:
            self._structure_view.setPlainText(entry.get("text", ""))
        self._structure_legend.show()
        self._structure_view.show()

    def _save_tags(self) -> None:
        if not self._current_entry:
            return
        tags_raw = self._tags_input.text().strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        self._entry_repo.update_tags(self._current_entry["id"], json.dumps(tags))
        self._current_entry["tags"] = json.dumps(tags)
        self._detail_text.setPlainText(self._format_detail(self._current_entry))
        self._status_label.setText("Saved tags.")

    def _save_related(self) -> None:
        if not self._current_entry:
            return
        entry_id = self._related_combo.currentData()
        if entry_id is None:
            return
        if entry_id not in self._current_related_ids:
            self._current_related_ids.append(entry_id)
        related_json = json.dumps(self._current_related_ids)
        self._entry_repo.update_related(self._current_entry["id"], related_json)
        self._current_entry["related_entry_ids"] = related_json
        self._detail_text.setPlainText(self._format_detail(self._current_entry))
        self._related_input.setText(self._format_related_terms(self._current_related_ids))
        self._status_label.setText("Added related word.")
        self._update_related_options(self._related_search.text())

    def _update_related_options(self, text: str) -> None:
        if not self._current_entry:
            self._related_combo.clear()
            return
        query = text.strip()
        self._related_combo.clear()
        exclude = [self._current_entry["id"], *self._current_related_ids]
        if not query:
            results = self._entry_repo.search_words("", exclude)
        else:
            results = self._entry_repo.search_words(query, exclude)
        if not results:
            self._status_label.setText("No related word matches.")
            return
        for row in results:
            self._related_combo.addItem(row["text"], row["id"])

    def _parse_related_ids(self, value: str) -> list:
        try:
            parsed = json.loads(value) if value else []
            if isinstance(parsed, list):
                normalized = []
                for item in parsed:
                    if isinstance(item, int):
                        normalized.append(item)
                    elif isinstance(item, str) and item.isdigit():
                        normalized.append(int(item))
                    else:
                        normalized.append(item)
                return normalized
        except Exception:
            pass
        return []

    def _format_related_terms(self, related_list: list) -> str:
        if not related_list:
            return ""
        ids = [item for item in related_list if isinstance(item, int)]
        texts = self._entry_repo.get_entry_texts(ids) if ids else {}
        resolved = []
        for item in related_list:
            if isinstance(item, int):
                resolved.append(texts.get(item, str(item)))
            else:
                resolved.append(str(item))
        return ", ".join(resolved)
