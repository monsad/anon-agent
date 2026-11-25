from docagent.anonymizer.detectors.dictionary import DictionaryDetector
from docagent.anonymizer.kinds import Kind

DETECTOR = DictionaryDetector(
    [("Hurtownia Paliw Kowalski", Kind.ORG), ("Jan Nowak", Kind.PERSON), ("  ", Kind.PERSON)]
)


def test_matches_case_insensitively():
    text = "Umowa z HURTOWNIA PALIW KOWALSKI oraz jan nowak."
    assert {(s.kind, s.text) for s in DETECTOR.detect(text)} == {
        (Kind.ORG, "HURTOWNIA PALIW KOWALSKI"),
        (Kind.PERSON, "jan nowak"),
    }


def test_does_not_match_inside_longer_word():
    assert DETECTOR.detect("Jan Nowakowski") == []
