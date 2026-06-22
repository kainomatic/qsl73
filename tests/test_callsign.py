import pytest
from qsl73.callsign import decompose_callsign, is_own_call

DEFAULT_SUFFIXES = ["P", "M", "MM", "AM", "QRP", "A", "R", "T"]


@pytest.mark.parametrize("call,expected", [
    # Kein Schrägstrich
    ("DK8XX", "DK8XX"),
    ("DL0AAA", "DL0AAA"),
    # Fall a: bekanntes Suffix
    ("DL1XXX/P", "DL1XXX"),
    ("DL0AAA/QRP", "DL0AAA"),
    ("K1ABC/M", "K1ABC"),
    ("UA4XXX/P", "UA4XXX"),
    ("DL0AAA/R", "DL0AAA"),
    # Fall b: bekannter ITU-Präfix
    ("5Z4/UA4XXX", "UA4XXX"),
    ("SV9/DL0AAA", "DL0AAA"),
    ("DL/DK1ABC", "DK1ABC"),
    ("UA9/DL1XXX", "DL1XXX"),
    # Fall c: mehrdeutig
    ("DL1ABC/IF9", None),
    ("G3ABC/W5XYZ", None),
])
def test_decompose_callsign(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


@pytest.mark.parametrize("call,expected", [
    ("DL1XXX/p", "DL1XXX"),
    ("dl1xxx/P", "DL1XXX"),
    ("5z4/UA4XXX", "UA4XXX"),
])
def test_decompose_callsign_case_insensitive(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


@pytest.mark.parametrize("call,own,stations,expected", [
    ("DL0AAA", "DL0AAA", set(), True),
    ("SV9/DL0AAA", "DL0AAA", set(), True),
    ("DL0AAA/P", "DL0AAA", set(), True),
    ("DO6XXX", "DL0AAA", {"DO6XXX"}, True),
    ("DO6XXX/P", "DL0AAA", {"DO6XXX"}, True),
    ("DK8XX", "DL0AAA", {"DO6XXX"}, False),
    ("DK8XX", "DL0AAA", set(), False),
    ("DF1DS/P", "DL0AAA", {"DF1DS"}, True),
])
def test_is_own_call(call, own, stations, expected):
    assert is_own_call(call, own, stations, DEFAULT_SUFFIXES) == expected


def test_is_own_call_ambiguous_returns_false():
    # IF9 → Fall c → decompose gibt None → False (vorsichtiges Verhalten)
    assert is_own_call("DL0AAA/IF9", "DL0AAA", set(), DEFAULT_SUFFIXES) is False


# ===========================================================================
# Kategorie D: Weitere ITU-Präfixe
# ===========================================================================

@pytest.mark.parametrize("call,expected", [
    ("VK2/DL0AAA",  "DL0AAA"),   # VK: Australien
    ("JA1/DL0AAA",  "DL0AAA"),   # JA: Japan (JA + Bezirksziffer)
    ("ON4/DK1ABC", "DK1ABC"),   # ON: Belgien
    ("ZL2/DL0AAA",  "DL0AAA"),   # ZL: Neuseeland
    ("VE3/DL0AAA",  "DL0AAA"),   # VE: Kanada
    ("LU5/DL0AAA",  "DL0AAA"),   # LU: Argentinien
    ("HS0/DL0AAA",  "DL0AAA"),   # HS: Thailand (HS + Bezirksziffer)
])
def test_decompose_additional_itu_prefixes(call, expected):
    assert decompose_callsign(call, DEFAULT_SUFFIXES) == expected


# ===========================================================================
# Kategorie D: Doppelter Zusatz (Präfix UND Suffix)
# ===========================================================================

def test_decompose_double_modifier_prefix_then_suffix():
    # "SV9/DL0AAA/P": split am ersten "/" → left="SV9" (ITU-Präfix) → right="DL0AAA/P"
    # right enthält noch "/" → wird direkt zurückgegeben, kein rekursiver Aufruf
    # Dokumentiert aktuelles Verhalten: "DL0AAA/P" (nicht None)
    # Sicherheits-Eigenschaft: führt in matching.py NIE zu CERTAIN (Dist 2 zu "DL0AAA")
    result = decompose_callsign("SV9/DL0AAA/P", DEFAULT_SUFFIXES)
    assert result == "DL0AAA/P"


def test_decompose_double_modifier_suffix_then_suffix():
    # "DL0AAA/P/MM": split am ersten "/" → left="DL0AAA", right="P/MM"
    # Fall a: "P/MM" ist kein bekanntes Portabel-Suffix → schlägt fehl
    # Fall b: "DL0AAA" ist kein ITU-Präfix → schlägt fehl
    # → Fall c: None (mehrdeutig, sicheres Verhalten)
    result = decompose_callsign("DL0AAA/P/MM", DEFAULT_SUFFIXES)
    assert result is None


# ===========================================================================
# Kategorie D: is_own_call — Portabel-Varianten und Auslandseinsätze
# ===========================================================================

@pytest.mark.parametrize("call,own,stations,expected", [
    ("DL0AAA/P",    "DL0AAA", set(),         True),   # Portabel-Suffix beim Hauptcall
    ("DL1XYZ/P",   "DL0AAA", set(),         False),  # Portabel, aber fremder Call
    ("VK2/DO6XXX", "DL0AAA", {"DO6XXX"},    True),   # Auslands-portabel, in stationcallsign
    ("ZL2/DL0AAA",  "DL0AAA", set(),         True),   # Eigener Call mit ITU-Präfix
    ("VK2/DK8XX",  "DL0AAA", {"DO6XXX"},   False),  # Fremder Call portabel im Ausland
])
def test_is_own_call_portable_variants(call, own, stations, expected):
    assert is_own_call(call, own, stations, DEFAULT_SUFFIXES) == expected
