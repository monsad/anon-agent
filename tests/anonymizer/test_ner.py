from dataclasses import dataclass

from docagent.anonymizer.detectors.ner import SpacyNerDetector
from docagent.anonymizer.kinds import Kind


@dataclass
class FakeEnt:
    text: str
    start_char: int
    label_: str

    @property
    def end_char(self) -> int:
        return self.start_char + len(self.text)


@dataclass
class FakeDoc:
    ents: list[FakeEnt]


def fake_nlp(text: str) -> FakeDoc:
    return FakeDoc(
        [
            FakeEnt("Jan Kowalski", text.index("Jan"), "persName"),
            FakeEnt("Orlen", text.index("Orlen"), "orgName"),
            FakeEnt("Katowice", text.index("Katowice"), "placeName"),
            FakeEnt("maja", text.index("maja"), "date"),
        ]
    )


def test_maps_spacy_labels_and_skips_others():
    text = "Jan Kowalski z Orlen, Katowice, 5 maja"
    spans = SpacyNerDetector(nlp=fake_nlp).detect(text)
    assert {(s.kind, s.text) for s in spans} == {
        (Kind.PERSON, "Jan Kowalski"),
        (Kind.ORG, "Orlen"),
        (Kind.ADDRESS, "Katowice"),
    }
    assert all(text[s.start : s.end] == s.text for s in spans)
