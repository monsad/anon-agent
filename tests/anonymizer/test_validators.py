import pytest

from docagent.anonymizer import validators as v


@pytest.mark.parametrize("value", ["1234563218", "123-456-32-18", "5252344078"])
def test_valid_nip(value):
    assert v.is_valid_nip(value)


@pytest.mark.parametrize("value", ["1234563219", "123456321", "0000123456"])
def test_invalid_nip(value):
    assert not v.is_valid_nip(value)


def test_pesel():
    assert v.is_valid_pesel("44051401359")
    assert not v.is_valid_pesel("44051401358")
    assert not v.is_valid_pesel("4405140135")


def test_regon_9_and_14_digits():
    assert v.is_valid_regon("123456785")
    assert not v.is_valid_regon("123456786")
    assert v.is_valid_regon("12345678512347")
    assert not v.is_valid_regon("12345678512348")


@pytest.mark.parametrize(
    "value",
    [
        "PL61109010140000071219812874",
        "PL61 1090 1014 0000 0712 1981 2874",
        "61109010140000071219812874",
    ],
)
def test_valid_iban(value):
    assert v.is_valid_iban(value)


def test_invalid_iban():
    assert not v.is_valid_iban("PL61109010140000071219812875")
    assert not v.is_valid_iban("PL61")


def test_id_card():
    assert v.is_valid_id_card("ABA300000")
    assert v.is_valid_id_card("aba 300000")
    assert not v.is_valid_id_card("ABA300001")
    assert not v.is_valid_id_card("AB1300000")
