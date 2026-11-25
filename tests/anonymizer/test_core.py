import re

import pytest

from docagent.anonymizer import (
    AnonymizationSettings,
    Anonymizer,
    DictionaryDetector,
    Kind,
    LeakDetected,
    PatternDetector,
    Span,
    restore,
)
from docagent.anonymizer.tokens import TOKEN_RE

INVOICE = (
    "Sprzedawca: Hurtownia Paliw Kowalski, NIP 123-456-32-18\n"
    "Kontakt: jan.kowalski@example.com\n"
    "Razem brutto: 1 234,56 zł"
)


def make(secret: bytes = b"firma-a", **settings) -> Anonymizer:
    detectors = [PatternDetector(), DictionaryDetector([("Hurtownia Paliw Kowalski", Kind.ORG)])]
    return Anonymizer(detectors, secret, AnonymizationSettings(**settings))


def test_masks_identifiers_and_keeps_amounts_by_default():
    result = make().anonymize(INVOICE)
    for secret_value in ("Hurtownia Paliw Kowalski", "123-456-32-18", "jan.kowalski@example.com"):
        assert secret_value not in result.text
    assert "1 234,56" in result.text
    assert len(TOKEN_RE.findall(result.text)) == 3


def test_roundtrip_restores_original_text():
    result = make().anonymize(INVOICE)
    assert restore(result.text, result.mapping) == INVOICE


def test_same_value_gets_same_token_across_documents():
    anonymizer = make()
    contract = anonymizer.anonymize("Umowa z Hurtownia Paliw Kowalski Sp. z o.o., NIP 1234563218")
    invoice = anonymizer.anonymize(INVOICE)
    shared = set(contract.mapping) & set(invoice.mapping)
    assert len(shared) == 2  # firma i NIP


def test_other_tenant_gets_different_tokens():
    assert not set(make(b"firma-a").anonymize(INVOICE).mapping) & set(
        make(b"firma-b").anonymize(INVOICE).mapping
    )


def test_amounts_masked_when_enabled():
    result = make(enabled_kinds=frozenset(Kind)).anonymize(INVOICE)
    assert "1 234,56" not in result.text


def test_restore_walks_llm_json_and_keeps_unknown_tokens():
    result = make().anonymize(INVOICE)
    nip_token = next(t for t in result.mapping if t.startswith("[NIP_"))
    llm_output = {"sprzedawca": {"nip": nip_token}, "pozycje": [nip_token, "[NIP_deadbeef]"], "netto": 100}
    assert restore(llm_output, result.mapping) == {
        "sprzedawca": {"nip": "123-456-32-18"},
        "pozycje": ["123-456-32-18", "[NIP_deadbeef]"],
        "netto": 100,
    }


def test_find_leaks_ignores_tokens_and_reports_raw_values():
    anonymizer = make()
    masked = anonymizer.anonymize("NIP 1234563218").text
    leaks = anonymizer.find_leaks(masked + " oraz 5252344078")
    assert [(s.kind, s.text) for s in leaks] == [(Kind.NIP, "5252344078")]


class SecondPassDetector:
    """Symuluje NER, który w drugim przebiegu znajduje coś, czego nie znalazł w pierwszym."""

    def __init__(self) -> None:
        self.calls = 0

    def detect(self, text: str) -> list[Span]:
        self.calls += 1
        if self.calls == 1 or "Kowalsky" not in text:
            return []
        start = text.index("Kowalsky")
        return [Span(start, start + len("Kowalsky"), Kind.PERSON, "Kowalsky")]


def test_second_pass_findings_are_masked_instead_of_blocking():
    text = "NIP 1234563218, Pan Kowalsky"
    result = Anonymizer([PatternDetector(), SecondPassDetector()], b"firma-a").anonymize(text)
    assert "Kowalsky" not in result.text and "1234563218" not in result.text
    assert restore(result.text, result.mapping) == text


class WordByWordDetector:
    """W każdym przebiegu zgłasza kolejne niezakryte słowo — nigdy się nie stabilizuje."""

    def detect(self, text: str) -> list[Span]:
        for match in re.finditer(r"\b[a-z]+\b", TOKEN_RE.sub(lambda m: "#" * len(m.group()), text)):
            return [Span(match.start(), match.end(), Kind.PERSON, match.group())]
        return []


def test_anonymize_blocks_when_leaks_do_not_go_away():
    anonymizer = Anonymizer([WordByWordDetector()], b"firma-a")
    with pytest.raises(LeakDetected) as error:
        anonymizer.anonymize("ala ma kota i psa")
    assert "psa" not in str(error.value)  # komunikat trafia do logów — bez danych
    assert error.value.spans[0].kind is Kind.PERSON
