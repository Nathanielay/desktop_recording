import re


WORD_RE = re.compile(r"^[A-Za-z][A-Za-z\-']*$")


def detect_entry_type(text: str) -> str:
    tokens = text.split()
    if len(tokens) == 1 and WORD_RE.match(tokens[0]):
        return "word"
    if 2 <= len(tokens) <= 6:
        return "phrase"
    return "article"


def is_english(text: str) -> bool:
    ascii_letters = sum(1 for c in text if "A" <= c <= "Z" or "a" <= c <= "z")
    total = sum(1 for c in text if c.isalpha())
    if total == 0:
        return False
    return ascii_letters / total >= 0.6
