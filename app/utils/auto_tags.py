import re
from typing import Iterable, List, Dict, Any


_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")

_PREFIXES = [
    "pro",
    "ex",
    "in",
    "im",
    "com",
    "re",
    "pre",
    "sub",
    "trans",
    "inter",
    "over",
    "under",
    "mis",
    "non",
    "anti",
]

_SUFFIXES = [
    "ship",
    "tion",
    "sion",
    "ment",
    "ness",
    "able",
    "ible",
    "ity",
    "ize",
    "ise",
    "ous",
    "ful",
    "less",
    "er",
    "or",
]


def build_auto_tags(
    word: str,
    translation: str,
    existing_words: Iterable[Dict[str, Any]],
) -> List[str]:
    tags = []
    lower_word = word.lower()

    for prefix in _PREFIXES:
        if lower_word.startswith(prefix):
            tags.append(f"root:{prefix}")

    for suffix in _SUFFIXES:
        if lower_word.endswith(suffix):
            tags.append(f"root:{suffix}")

    cn_tokens = set(_extract_cn_tokens(translation))
    if cn_tokens:
        for row in existing_words:
            other_translation = row.get("translation", "")
            other_tokens = set(_extract_cn_tokens(other_translation))
            shared = cn_tokens.intersection(other_tokens)
            for token in shared:
                tags.append(f"cn_shared:{token}")

    for row in existing_words:
        other_word = str(row.get("text", "")).strip()
        if not other_word:
            continue
        other_lower = other_word.lower()
        if lower_word == other_lower:
            continue
        if lower_word in other_lower or other_lower in lower_word:
            tags.append(f"overlap:{other_word}")

    return _dedupe(tags)


def _extract_cn_tokens(text: str) -> List[str]:
    return _CJK_RE.findall(text or "")


def _dedupe(items: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
