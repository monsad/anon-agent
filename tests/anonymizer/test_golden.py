from pathlib import Path

from docagent.anonymizer import Anonymizer, PatternDetector
from docagent.anonymizer.evaluation import STRUCTURED, failures, load_samples, recall_by_kind

GOLDEN = Path(__file__).parent / "fixtures" / "golden.jsonl"


def test_structured_identifiers_are_always_caught():
    counts = recall_by_kind(Anonymizer([PatternDetector()], b"eval"), load_samples(GOLDEN))
    structured = {kind: c for kind, c in counts.items() if kind in STRUCTURED}
    assert structured, "zestaw testowy nie ma identyfikatorów"
    assert failures(structured) == []


def test_missing_person_lowers_recall():
    counts = recall_by_kind(Anonymizer([PatternDetector()], b"eval"), load_samples(GOLDEN))
    found, total = counts["PERSON"]
    assert (found, total) == (0, 1)  # bez NER nazwisk nie łapiemy — pomiar musi to pokazać
