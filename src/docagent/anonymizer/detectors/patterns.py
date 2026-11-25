import re
from collections.abc import Callable

from docagent.anonymizer import validators as v
from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.spans import Span

# (?<!\d) / (?!\d) zamiast \b, żeby łapać też "PL1234563218".
_SEP = r"[- ]?"
_CAP = "[A-ZĄĆĘŁŃÓŚŹŻ]"
_RULES: list[tuple[Kind, re.Pattern[str], Callable[[str], bool] | None]] = [
    (Kind.IBAN, re.compile(r"(?<!\d)(?:PL ?)?\d{2}(?: ?\d{4}){6}(?!\d)"), v.is_valid_iban),
    (Kind.PESEL, re.compile(r"(?<!\d)\d{11}(?!\d)"), v.is_valid_pesel),
    (
        Kind.NIP,
        re.compile(
            rf"(?<!\d)(?:\d{{3}}{_SEP}\d{{3}}{_SEP}\d{{2}}{_SEP}\d{{2}}"
            rf"|\d{{3}}{_SEP}\d{{2}}{_SEP}\d{{2}}{_SEP}\d{{3}})(?!\d)"
        ),
        v.is_valid_nip,
    ),
    (Kind.REGON, re.compile(r"(?<!\d)(?:\d{14}|\d{9})(?!\d)"), v.is_valid_regon),
    (Kind.KRS, re.compile(r"\bKRS[:\s]*(?P<value>\d{10})(?!\d)"), None),
    (Kind.ID_CARD, re.compile(r"\b[A-Z]{3} ?\d{6}(?!\d)"), v.is_valid_id_card),
    (Kind.EMAIL, re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), None),
    (Kind.PHONE, re.compile(r"(?<![\d+])(?:\+48[ -]?)?\d{3}[ -]?\d{3}[ -]?\d{3}(?!\d)"), None),
    (Kind.POSTAL_CODE, re.compile(r"(?<!\d)\d{2}-\d{3}(?!\d)"), None),
    # Kwota: z groszami albo z walutą; tysiące oddzielone spacją, twardą spacją lub kropką.
    (
        Kind.AMOUNT,
        re.compile(
            r"(?<![\d,.])\d{1,3}(?:[ \u00a0.]?\d{3})*"
            r"(?:,\d{2}(?!\d)(?: ?(?:zł|złotych|PLN|EUR|euro|USD)\b)?"
            r"|(?:,\d{2})? ?(?:zł|złotych|PLN|EUR|euro|USD)\b)"
        ),
        None,
    ),
    (Kind.AMOUNT, re.compile(r"\(?(?i:słownie)\b:?[^)\n]*\)?"), None),
    # Nazwa firmy zakończona formą prawną — NER zwykle tnie "Sp. z o.o." i "S.A." na kawałki.
    (
        Kind.ORG,
        re.compile(
            rf"\b{_CAP}[\w&-]*(?: {_CAP}[\w&-]*){{0,4}}"
            r" (?:[Ss]p\. z o\. ?o\.|S\.A\.|[Ss]p\. [jkp]\.|s\.c\."
            r"|(?i:spółka z ograniczoną odpowiedzialnością|spółka akcyjna|spółka jawna|spółka komandytowa"
            r"|spółka cywilna))"
        ),
        None,
    ),
    (Kind.ADDRESS, re.compile(rf"\b(?:ul|al|pl|os)\. {_CAP}[\w-]*(?: {_CAP}[\w-]*)* \d+[a-zA-Z]?(?:/\d+)?"), None),
]


class PatternDetector:
    """Identyfikatory o stałym formacie; tam gdzie się da, z walidacją sumy kontrolnej."""

    def detect(self, text: str) -> list[Span]:
        spans: list[Span] = []
        for kind, pattern, validator in _RULES:
            group = "value" if "value" in pattern.groupindex else 0
            for match in pattern.finditer(text):
                value = match.group(group)
                if validator is None or validator(value):
                    spans.append(Span(match.start(group), match.end(group), kind, value))
        return spans
