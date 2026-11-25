from dataclasses import dataclass

from docagent.anonymizer.kinds import PRIORITY, Kind


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: Kind
    text: str

    def overlaps(self, other: "Span") -> bool:
        return self.start < other.end and other.start < self.end


def resolve_overlaps(spans: list[Span]) -> list[Span]:
    """Zostawia rozłączne wykrycia: dłuższe wygrywa, przy remisie wyższy priorytet."""
    ranked = sorted(spans, key=lambda s: (-(s.end - s.start), PRIORITY[s.kind], s.start))
    chosen: list[Span] = []
    for span in ranked:
        if not any(span.overlaps(c) for c in chosen):
            chosen.append(span)
    return sorted(chosen, key=lambda s: s.start)
