import pytest

from docagent.anonymizer.detectors.patterns import PatternDetector
from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.spans import resolve_overlaps


def found(text: str) -> set[tuple[Kind, str]]:
    return {(s.kind, s.text) for s in resolve_overlaps(PatternDetector().detect(text))}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("NIP: 123-456-32-18", (Kind.NIP, "123-456-32-18")),
        ("NIP PL1234563218", (Kind.NIP, "1234563218")),
        ("PESEL 44051401359", (Kind.PESEL, "44051401359")),
        ("REGON 123456785", (Kind.REGON, "123456785")),
        ("konto PL61 1090 1014 0000 0712 1981 2874.", (Kind.IBAN, "PL61 1090 1014 0000 0712 1981 2874")),
        ("konto 61109010140000071219812874", (Kind.IBAN, "61109010140000071219812874")),
        ("(KRS 0000123456)", (Kind.KRS, "0000123456")),
        ("dowód ABA300000", (Kind.ID_CARD, "ABA300000")),
        ("pisz: jan.kowalski@example.com", (Kind.EMAIL, "jan.kowalski@example.com")),
        ("tel. +48 601 234 567", (Kind.PHONE, "+48 601 234 567")),
        ("40-001 Katowice", (Kind.POSTAL_CODE, "40-001")),
        ("Razem 1 234,56 zł", (Kind.AMOUNT, "1 234,56 zł")),
        ("Kwota 153.750,00 PLN brutto", (Kind.AMOUNT, "153.750,00 PLN")),
        ("max 10 000 zł", (Kind.AMOUNT, "10 000 zł")),
        ("cena 5000 EUR", (Kind.AMOUNT, "5000 EUR")),
        ("(słownie: sto złotych)", (Kind.AMOUNT, "(słownie: sto złotych)")),
        ("Nabywca: Petrotest S.A., NIP", (Kind.ORG, "Petrotest S.A.")),
        ("od Hurtownia Paliw Kowalski Sp. z o.o.", (Kind.ORG, "Hurtownia Paliw Kowalski Sp. z o.o.")),
        ("adres: ul. Długa 5,", (Kind.ADDRESS, "ul. Długa 5")),
        (
            "Nazwa: TRANSPALIWA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ\n",
            (Kind.ORG, "TRANSPALIWA SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ"),
        ),
    ],
)
def test_detects_kind(text, expected):
    assert found(text) == {expected}


def test_number_with_bad_checksum_is_ignored():
    assert found("NIP 1234563219") == set()


def test_span_offsets_point_at_value():
    text = "NIP PL1234563218"
    [span] = resolve_overlaps(PatternDetector().detect(text))
    assert text[span.start : span.end] == "1234563218"
