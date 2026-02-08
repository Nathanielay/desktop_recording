import html
from typing import Dict, Any, Optional


class GrammarService:
    def __init__(self) -> None:
        self._nlp = self._load_spacy()

    def analyze(self, sentence: str) -> Dict[str, Any]:
        if not self._nlp:
            return {
                "structure_tags": {
                    "subject": "",
                    "verb": "",
                    "object": "",
                    "clause_type": "unknown",
                },
                "hints": [
                    "Parser unavailable. Install spaCy and en_core_web_sm.",
                    "Identify the main subject and verb first.",
                ],
                "rule_ids": ["parser-missing-01"],
                "summary": "Parser not available.",
            }

        doc = self._nlp(sentence)
        root = self._find_root(doc)
        subject = self._find_dep(doc, {"nsubj", "nsubjpass"})
        obj = self._find_dep(doc, {"dobj", "obj", "pobj"})
        clause_type = self._detect_clause_type(doc)
        clause_tokens = self._clause_tokens(doc)

        hints = self._build_hints(subject, root, obj, clause_type)
        return {
            "structure_tags": {
                "subject": subject.text if subject else "",
                "verb": root.text if root else "",
                "object": obj.text if obj else "",
                "clause_type": clause_type,
            },
            "hints": hints,
            "rule_ids": [f"clause-{clause_type}"],
            "summary": f"S:{subject.text if subject else '-'} V:{root.text if root else '-'} O:{obj.text if obj else '-'}",
            "highlighted_html": self._highlight_html(doc, subject, root, obj, clause_tokens),
        }

    def _load_spacy(self) -> Optional["spacy.language.Language"]:
        try:
            import spacy
        except Exception:
            return None
        for model in ("en_core_web_sm", "en_core_web_trf"):
            try:
                return spacy.load(model)
            except Exception:
                continue
        return None

    def _find_root(self, doc) -> Optional["spacy.tokens.Token"]:
        for token in doc:
            if token.dep_ == "ROOT":
                return token
        return None

    def _find_dep(self, doc, dep_labels: set) -> Optional["spacy.tokens.Token"]:
        for token in doc:
            if token.dep_ in dep_labels:
                return token
        return None

    def _detect_clause_type(self, doc) -> str:
        for token in doc:
            if token.dep_ == "relcl":
                return "relative"
            if token.dep_ in {"ccomp", "xcomp"}:
                return "noun"
            if token.dep_ == "advcl":
                return "adverbial"
        return "main"

    def _clause_tokens(self, doc) -> set:
        clause_heads = [t for t in doc if t.dep_ in {"relcl", "advcl", "ccomp", "xcomp"}]
        tokens = set()
        for head in clause_heads:
            tokens.update(list(head.subtree))
        return tokens

    def _highlight_html(self, doc, subject, root, obj, clause_tokens: set) -> str:
        subject_id = subject.i if subject else -1
        root_id = root.i if root else -1
        obj_id = obj.i if obj else -1
        parts = []
        for token in doc:
            word = html.escape(token.text)
            style = ""
            if token.i == subject_id:
                style = "background-color:#ffe8a3;"
            elif token.i == root_id:
                style = "background-color:#ffd1d1;"
            elif token.i == obj_id:
                style = "background-color:#d8f5d1;"
            elif token in clause_tokens:
                style = "background-color:#d9ecff;"
            if style:
                word = f"<span style='{style}'>{word}</span>"
            parts.append(word + ("" if token.whitespace_ == "" else " "))
        return "".join(parts)

    def _build_hints(self, subject, root, obj, clause_type: str) -> list:
        hints = []
        if subject and root:
            hints.append(f"Main clause: {subject.text} → {root.text}.")
        if obj:
            hints.append(f"Identify object: {obj.text}.")
        if clause_type != "main":
            hints.append(f"Clause type detected: {clause_type}.")
        if not hints:
            hints.append("Try isolating the main clause first.")
        return hints
