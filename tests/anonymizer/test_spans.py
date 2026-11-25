from docagent.anonymizer.kinds import DEFAULT_KINDS, Kind
from docagent.anonymizer.spans import Span, resolve_overlaps


def test_disjoint_spans_are_kept_in_text_order():
    a = Span(10, 15, Kind.EMAIL, "x")
    b = Span(0, 5, Kind.NIP, "y")
    assert resolve_overlaps([a, b]) == [b, a]


def test_longer_span_wins_overlap():
    postal = Span(7, 13, Kind.POSTAL_CODE, "67-890")
    nip = Span(0, 13, Kind.NIP, "123-45-67-890")
    assert resolve_overlaps([postal, nip]) == [nip]


def test_equal_length_overlap_uses_priority():
    phone = Span(0, 9, Kind.PHONE, "123456785")
    regon = Span(0, 9, Kind.REGON, "123456785")
    assert resolve_overlaps([phone, regon]) == [regon]


def test_amounts_are_not_masked_by_default():
    assert Kind.AMOUNT not in DEFAULT_KINDS
    assert Kind.NIP in DEFAULT_KINDS
