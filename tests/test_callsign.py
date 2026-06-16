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


# ===========================================================================
# Kategorie D: Weitere ITU-Präfixe
# ===========================================================================

@pytest.mark.parametrize("call,expected", [
    ("VK2/DH3KR",  "DH3KR"),   # VK: Australien
    ("JA1/DH3KR",  "DH3KR"),   # JA: Japan (JA + Bezirksziffer)
    ("ON4/DK1ABC", "DK1ABC"),   # ON: Belgien
    ("ZL2/DH3KR",  "DH3KR"),   # ZL: Neuseeland
    ("VE3/DH3KR",  "DH3KR"),   # VE: Kanada
    ("LU5/DH3KR",  "DH3KR"),   # LU: Argentinien
    ("HS0/DH3KR",  "DH3KR"),   # HS: Thailand (HS + Bezirksziffer)
])
def test_decompose_additional_itu_prefixes(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


# ===========================================================================
# Kategorie D: Doppelter Zusatz (Präfix UND Suffix)
# ===========================================================================

def test_decompose_double_modifier_prefix_then_suffix():
    # "SV9/DH3KR/P": split am ersten "/" → left="SV9" (ITU-Präfix) → right="DH3KR/P"
    # right enthält noch "/" → wird direkt zurückgegeben, kein rekursiver Aufruf
    # Dokumentiert aktuelles Verhalten: "DH3KR/P" (nicht None)
    # Sicherheits-Eigenschaft: führt in matching.py NIE zu CERTAIN (Dist 2 zu "DH3KR")
    result = decompose_callsign("SV9/DH3KR/P", DEFAULT_SUFFIXES)
    assert result == "DH3KR/P"


def test_decompose_double_modifier_suffix_then_suffix():
    # "DH3KR/P/MM": split am ersten "/" → left="DH3KR", right="P/MM"
    # Fall a: "P/MM" ist kein bekanntes Portabel-Suffix → schlägt fehl
    # Fall b: "DH3KR" ist kein ITU-Präfix → schlägt fehl
    # → Fall c: None (mehrdeutig, sicheres Verhalten)
    result = decompose_callsign("DH3KR/P/MM", DEFAULT_SUFFIXES)
    assert result is None


# ===========================================================================
# Kategorie D: is_own_call — Portabel-Varianten und Auslandseinsätze
# ===========================================================================

@pytest.mark.parametrize("call,own,stations,expected", [
    ("DH3KR/P",    "DH3KR", set(),         True),   # Portabel-Suffix beim Hauptcall
    ("DL1XYZ/P",   "DH3KR", set(),         False),  # Portabel, aber fremder Call
    ("VK2/DO6KBO", "DH3KR", {"DO6KBO"},    True),   # Auslands-portabel, in stationcallsign
    ("ZL2/DH3KR",  "DH3KR", set(),         True),   # Eigener Call mit ITU-Präfix
    ("VK2/DK8NE",  "DH3KR", {"DO6KBO"},   False),  # Fremder Call portabel im Ausland
])
def test_is_own_call_portable_variants(call, own, stations, expected):
    assert is_own_call(call, own, stations, DEFAULT_SUFFIXES) == expected
