from docagent.anonymizer.kinds import Kind
from docagent.anonymizer.normalize import normalize
from docagent.anonymizer.tokens import TOKEN_RE, make_token

SECRET = b"firma-a"


def test_formatting_variants_share_a_token():
    assert make_token(SECRET, Kind.NIP, "123-456-32-18") == make_token(SECRET, Kind.NIP, "1234563218")
    assert make_token(SECRET, Kind.ORG, "Hurtownia Kowalski Sp. z o.o.") == make_token(
        SECRET, Kind.ORG, "HURTOWNIA  KOWALSKI"
    )
    assert make_token(SECRET, Kind.PHONE, "+48 601 234 567") == make_token(SECRET, Kind.PHONE, "601234567")


def test_tenant_secret_and_kind_change_the_token():
    token = make_token(SECRET, Kind.NIP, "1234563218")
    assert token != make_token(b"firma-b", Kind.NIP, "1234563218")
    assert token != make_token(SECRET, Kind.PESEL, "1234563218")


def test_token_format():
    token = make_token(SECRET, Kind.POSTAL_CODE, "40-001")
    match = TOKEN_RE.fullmatch(token)
    assert match and match["kind"] == "POSTAL_CODE"


def test_normalize_org_strips_legal_form_and_quotes():
    assert normalize(Kind.ORG, '„Paliwex" S.A.') == "paliwex"
    assert normalize(Kind.EMAIL, " Jan@Example.COM ") == "jan@example.com"
