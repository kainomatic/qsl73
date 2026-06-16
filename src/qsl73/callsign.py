"""Rufzeichen-Zerlegung und Eigenrufzeichen-Prüfung.

3-Fall-Logik gemäß KONZEPT.md §6.3 und ADR-0013:
  a) Suffix bekannt  → Teil vor /  ist Stamm
  b) Präfix bekannt  → Teil nach / ist Stamm
  c) Mehrdeutig      → None (führt zu MatchResult.UNCERTAIN)
"""
from __future__ import annotations

from typing import Optional

from qsl73.data.itu_prefixes import is_itu_prefix


def decompose_callsign(call: str, portable_suffixes: list[str]) -> Optional[str]:
    """Zerlegt Rufzeichen mit / in Stammrufzeichen.

    Gibt None zurück wenn die Zerlegung mehrdeutig ist (Fall c).
    Gibt das Rufzeichen zurück (uppercase) wenn kein / enthalten.
    """
    call = call.strip().upper()
    if "/" not in call:
        return call

    left, right = call.split("/", 1)

    # Fall a: rechter Teil ist bekanntes Portabel-Suffix
    suffixes_upper = {s.upper() for s in portable_suffixes}
    if right in suffixes_upper:
        return left

    # Fall b: linker Teil ist bekannter ITU-Länderpräfix
    if is_itu_prefix(left):
        return right

    # Fall c: mehrdeutig
    return None


def is_own_call(
    call: str,
    own_callsign: str,
    station_callsigns: set[str],
    portable_suffixes: list[str],
) -> bool:
    """Prüft ob call (nach Zerlegung) zu einem eigenen Rufzeichen gehört.

    Bei nicht zerlegbarem call (Fall c) → False (vorsichtiges Verhalten).
    """
    call_base = decompose_callsign(call, portable_suffixes)
    if call_base is None:
        return False

    own_base = decompose_callsign(own_callsign, portable_suffixes) or own_callsign.upper()
    if call_base == own_base:
        return True

    for sc in station_callsigns:
        sc_base = decompose_callsign(sc, portable_suffixes) or sc.upper().strip()
        if call_base == sc_base:
            return True

    return False
