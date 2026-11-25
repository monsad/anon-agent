import json
from dataclasses import dataclass
from pathlib import Path

from docagent.anonymizer.core import Anonymizer
from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.spans import Span

STRUCTURED = frozenset(
    {Kind.NIP, Kind.PESEL, Kind.REGON, Kind.KRS, Kind.IBAN, Kind.ID_CARD, Kind.EMAIL, Kind.PHONE, Kind.POSTAL_CODE}
)
THRESHOLDS: dict[Kind, float] = {
    **{kind: 1.0 for kind in STRUCTURED},
    Kind.PERSON: 0.98,
    Kind.ORG: 0.98,
    Kind.ADDRESS: 0.98,
}


@dataclass(frozen=True)
class Sample:
    id: str
    text: str
    entities: list[tuple[Kind, str]]


def load_samples(path: Path) -> list[Sample]:
    samples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            entities = [(Kind(e["kind"]), e["text"]) for e in row["entities"]]
            samples.append(Sample(row["id"], row["text"], entities))
    return samples


def _is_covered(text: str, value: str, spans: list[Span]) -> bool:
    """Każde wystąpienie wartości musi być w całości zakryte jakimś wykryciem (rodzaj bez znaczenia)."""
    start = text.find(value)
    if start < 0:
        raise ValueError("wartość z zestawu testowego nie występuje w tekście")
    while start >= 0:
        end = start + len(value)
        if not any(s.start <= start and s.end >= end for s in spans):
            return False
        start = text.find(value, start + 1)
    return True


def recall_by_kind(anonymizer: Anonymizer, samples: list[Sample]) -> dict[Kind, tuple[int, int]]:
    counts: dict[Kind, tuple[int, int]] = {}
    for sample in samples:
        spans = anonymizer.detect(sample.text)
        for kind, value in sample.entities:
            found, total = counts.get(kind, (0, 0))
            counts[kind] = (found + _is_covered(sample.text, value, spans), total + 1)
    return counts


def failures(counts: dict[Kind, tuple[int, int]]) -> list[Kind]:
    return [kind for kind, (found, total) in counts.items() if total and found / total < THRESHOLDS.get(kind, 1.0)]
