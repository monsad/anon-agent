NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)
PESEL_WEIGHTS = (1, 3, 7, 9, 1, 3, 7, 9, 1, 3)
REGON9_WEIGHTS = (8, 9, 2, 3, 4, 5, 6, 7)
REGON14_WEIGHTS = (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8)
# Cyfra kontrolna dowodu stoi na 4. pozycji i ma wagę 9 (≡ -1 mod 10).
ID_CARD_WEIGHTS = (7, 3, 1, 9, 7, 3, 1, 7, 3)


def digits(value: str) -> str:
    return "".join(c for c in value if c.isascii() and c.isdigit())


def _weighted(ds: str, weights: tuple[int, ...]) -> int:
    return sum(int(d) * w for d, w in zip(ds, weights))


def is_valid_nip(value: str) -> bool:
    ds = digits(value)
    if len(ds) != 10:
        return False
    check = _weighted(ds, NIP_WEIGHTS) % 11
    return check != 10 and check == int(ds[9])


def is_valid_pesel(value: str) -> bool:
    ds = digits(value)
    if len(ds) != 11:
        return False
    return (10 - _weighted(ds, PESEL_WEIGHTS) % 10) % 10 == int(ds[10])


def is_valid_regon(value: str) -> bool:
    ds = digits(value)
    if len(ds) == 9:
        weights = REGON9_WEIGHTS
    elif len(ds) == 14:
        weights = REGON14_WEIGHTS
    else:
        return False
    return _weighted(ds, weights) % 11 % 10 == int(ds[-1])


def is_valid_iban(value: str) -> bool:
    s = value.replace(" ", "").upper()
    if s.isdigit() and len(s) == 26:  # polski NRB bez prefiksu kraju
        s = "PL" + s
    if len(s) < 15 or not s[:2].isalpha() or not s[2:].isalnum():
        return False
    rearranged = s[4:] + s[:4]
    return int("".join(str(int(c, 36)) for c in rearranged)) % 97 == 1


def is_valid_id_card(value: str) -> bool:
    s = value.replace(" ", "").upper()
    if len(s) != 9 or not s[:3].isalpha() or not s[3:].isdigit():
        return False
    return sum(int(c, 36) * w for c, w in zip(s, ID_CARD_WEIGHTS)) % 10 == 0
