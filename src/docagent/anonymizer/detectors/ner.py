from collections.abc import Callable
from typing import Any

from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.spans import Span

SPACY_LABELS: dict[str, Kind] = {
    "persName": Kind.PERSON,
    "orgName": Kind.ORG,
    "placeName": Kind.ADDRESS,
    "geogName": Kind.ADDRESS,
}


class SpacyNerDetector:
    """Osoby, firmy i miejsca z polskiego modelu spaCy (pip install 'docagent[ner]')."""

    def __init__(self, nlp: Callable[[str], Any] | None = None, model: str = "pl_core_news_lg"):
        if nlp is None:
            import spacy

            nlp = spacy.load(model)
        self._nlp = nlp

    def detect(self, text: str) -> list[Span]:
        return [
            Span(ent.start_char, ent.end_char, SPACY_LABELS[ent.label_], ent.text)
            for ent in self._nlp(text).ents
            if ent.label_ in SPACY_LABELS and len(ent.text.strip(" .,")) >= 3  # odrzuca "A.", "ul."
        ]
