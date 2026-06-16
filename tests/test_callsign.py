import pytest
from qsl73.callsign import decompose_callsign, is_own_call

DEFAULT_SUFFIXES = ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]


@pytest.mark.parametrize("call,expected", [
    # Kein Schrägstrich
    ("DK8NE", "DK8NE"),
    ("DH3KR", "DH3KR"),
    # Fall a: bekanntes Suffix
    ("DL1EJD/P", "DL1EJD"),
    ("DH3KR/QRP", "DH3KR"),
    ("K1ABC/M", "K1ABC"),
    ("UA4WHX/P", "UA4WHX"),
    ("DH3KR/R", "DH3KR"),
    # Fall b: bekannter ITU-Präfix
    ("5Z4/UA4WHX", "UA4WHX"),
    ("SV9/DH3KR", "DH3KR"),
    ("DL/DK1ABC", "DK1ABC"),
    ("UA9/DL1EJD", "DL1EJD"),
    # Fall c: mehrdeutig
    ("DL1ABC/IF9", None),
    ("G3ABC/W5XYZ", None),
])
def test_decompose_callsign(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


@pytest.mark.parametrize("call,expected", [
    ("DL1EJD/p", "DL1EJD"),
    ("dl1ejd/P", "DL1EJD"),
    ("5z4/UA4WHX", "UA4WHX"),
])
def test_decompose_callsign_case_insensitive(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


@pytest.mark.parametrize("call,own,stations,expected", [
    ("DH3KR", "DH3KR", set(), True),
    ("SV9/DH3KR", "DH3KR", set(), True),
    ("DH3KR/P", "DH3KR", set(), True),
    ("DO6KBO", "DH3KR", {"DO6KBO"}, True),
    ("DO6KBO/P", "DH3KR", {"DO6KBO"}, True),
    ("DK8NE", "DH3KR", {"DO6KBO"}, False),
    ("DK8NE", "DH3KR", set(), False),
    ("DF1DS/P", "DH3KR", {"DF1DS"}, True),
])
def test_is_own_call(call, own, stations, expected):
    assert is_own_call(call, own, stations, DEFAULT_SUFFIXES) == expected


def test_is_own_call_ambiguous_returns_false():
    # IF9 → Fall c → decompose gibt None → False (vorsichtiges Verhalten)
    assert is_own_call("DH3KR/IF9", "DH3KR", set(), DEFAULT_SUFFIXES) is False
