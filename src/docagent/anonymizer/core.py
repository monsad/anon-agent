from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from docagent.anonymizer.detectors import Detector
from docagent.anonymizer.kinds import DEFAULT_KINDS, Kind
from docagent.anonymizer.spans import Span, resolve_overlaps
from docagent.anonymizer.tokens import TOKEN_RE, make_token


MAX_PASSES = 3


@dataclass(frozen=True)
class AnonymizationSettings:
    enabled_kinds: frozenset[Kind] = DEFAULT_KINDS


@dataclass(frozen=True)
class AnonymizationResult:
    text: str
    mapping: dict[str, str]  # znacznik -> pierwsza napotkana postać oryginału


class LeakDetected(Exception):
    def __init__(self, spans: list[Span]):
        kinds = ", ".join(sorted({s.kind.value for s in spans}))
        super().__init__(f"Po anonimizacji zostały nieukryte dane: {kinds}")
        self.spans = spans


class Anonymizer:
    def __init__(
        self,
        detectors: Sequence[Detector],
        secret: bytes,
        settings: AnonymizationSettings = AnonymizationSettings(),
    ):
        self._detectors = list(detectors)
        self._secret = secret
        self._settings = settings

    def detect(self, text: str) -> list[Span]:
        spans = [
            span
            for detector in self._detectors
            for span in detector.detect(text)
            if span.kind in self._settings.enabled_kinds
        ]
        return resolve_overlaps(spans)

    def anonymize(self, text: str) -> AnonymizationResult:
        # NER bywa niestabilny: w tekście ze znacznikami potrafi znaleźć coś nowego.
        # Takie znaleziska zakrywamy w kolejnym przebiegu; blokujemy dopiero, gdy nie znikają.
        mapping: dict[str, str] = {}
        masked = text
        for _ in range(MAX_PASSES):
            spans = self.find_leaks(masked)
            if not spans:
                break
            masked = self._mask(masked, spans, mapping)
        if leaks := self.find_leaks(masked):
            raise LeakDetected(leaks)
        return AnonymizationResult(masked, mapping)

    def _mask(self, text: str, spans: list[Span], mapping: dict[str, str]) -> str:
        parts: list[str] = []
        pos = 0
        for span in spans:
            token = make_token(self._secret, span.kind, span.text)
            mapping.setdefault(token, span.text)
            parts += [text[pos : span.start], token]
            pos = span.end
        parts.append(text[pos:])
        return "".join(parts)

    def find_leaks(self, masked_text: str) -> list[Span]:
        """Bezpiecznik: wykrycia w tekście po anonimizacji, poza samymi znacznikami."""
        tokens = [Span(m.start(), m.end(), Kind.ORG, m.group()) for m in TOKEN_RE.finditer(masked_text)]
        return [s for s in self.detect(masked_text) if not any(s.overlaps(t) for t in tokens)]


def restore(value: Any, mapping: dict[str, str]) -> Any:
    """Podstawia prawdziwe wartości w tekście albo w JSON-ie (dict/list) z odpowiedzi LLM."""
    if isinstance(value, str):
        return TOKEN_RE.sub(lambda m: mapping.get(m.group(), m.group()), value)
    if isinstance(value, list):
        return [restore(item, mapping) for item in value]
    if isinstance(value, dict):
        return {key: restore(item, mapping) for key, item in value.items()}
    return value
