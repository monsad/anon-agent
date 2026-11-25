import re

from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.validators import digits

_QUOTES = re.compile(r"[\"'„”“«»]")
_SPACES = re.compile(r"\s+")
_LEGAL_FORM = re.compile(r"\s+(sp\.?\s*z\.?\s*o\.?\s*o\.?|s\.?\s*a\.?|sp\.?\s*[jkp]\.?|s\.?\s*c\.?)\s*$")


def _simplify(value: str) -> str:
    return _SPACES.sub(" ", _QUOTES.sub("", value.lower())).strip()


def normalize(kind: Kind, value: str) -> str:
    """Postać kanoniczna — różne zapisy tej samej wartości dają ten sam znacznik."""
    match kind:
        case Kind.NIP | Kind.PESEL | Kind.REGON | Kind.KRS | Kind.POSTAL_CODE | Kind.IBAN:
            return digits(value)
        case Kind.PHONE:
            return digits(value)[-9:]
        case Kind.ID_CARD:
            return value.replace(" ", "").upper()
        case Kind.EMAIL:
            return value.strip().lower()
        case Kind.ORG:
            return _LEGAL_FORM.sub("", _simplify(value))
        case _:
            return _simplify(value)
