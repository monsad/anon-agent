import re
from collections.abc import Iterable

from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.spans import Span


class DictionaryDetector:
    """Wartości już znane firmie (kontrahenci, pracownicy) — łapane nawet gdy NER je przeoczy."""

    def __init__(self, entries: Iterable[tuple[str, Kind]]):
        unique = {(text.strip(), kind) for text, kind in entries if text.strip()}
        self._rules = [
            (kind, re.compile(rf"(?<!\w){re.escape(text)}(?!\w)", re.IGNORECASE))
            for text, kind in sorted(unique, key=lambda e: -len(e[0]))
        ]

    def detect(self, text: str) -> list[Span]:
        return [
            Span(m.start(), m.end(), kind, m.group())
            for kind, pattern in self._rules
            for m in pattern.finditer(text)
        ]
