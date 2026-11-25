from enum import StrEnum


class Kind(StrEnum):
    IBAN = "IBAN"
    PESEL = "PESEL"
    NIP = "NIP"
    REGON = "REGON"
    KRS = "KRS"
    ID_CARD = "ID_CARD"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    POSTAL_CODE = "POSTAL_CODE"
    PERSON = "PERSON"
    ORG = "ORG"
    ADDRESS = "ADDRESS"
    AMOUNT = "AMOUNT"


# Kolejność w Kind = priorytet przy nakładających się wykryciach tej samej długości.
PRIORITY: dict[Kind, int] = {kind: i for i, kind in enumerate(Kind)}

# Kwoty nie są danymi osobowymi; firma może je włączyć w ustawieniach.
DEFAULT_KINDS: frozenset[Kind] = frozenset(Kind) - {Kind.AMOUNT}
