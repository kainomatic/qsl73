"""ITU-Länderpräfix-Liste für Rufzeichen-Zerlegung (ADR-0013).

Quelle: ARRL DXCC-Länderliste / ITU-Präfixzuteilungen, Stand 2025.
Zur Erweiterung: Präfix in PREFIXES aufnehmen (als Großbuchstaben-String).
Enthält gängige Expeditions-/Portable-Präfixe inkl. Insel-/Gebietsvarianten.

Verwendung: is_itu_prefix(part) prüft, ob der linke Teil eines callsign/suffix-
Ausdrucks ein bekannter ITU-Länderpräfix ist (einschließlich Präfix + Bezirksziffer).
"""

from __future__ import annotations

# Bare ITU-Präfixe (ohne Bezirksziffer).
# is_itu_prefix() akzeptiert auch Präfix + eine abschließende Ziffer (Bezirk).
PREFIXES: frozenset[str] = frozenset({
    # Europa
    "CT", "CT1", "CT2", "CT3",
    "CU",
    "DA", "DB", "DC", "DD", "DE", "DF", "DG", "DH", "DI", "DJ", "DK", "DL",
    "DM", "DN", "DO", "DP", "DQ", "DR",
    "EA", "EA6", "EA8", "EA9",
    "EB", "EC", "ED", "EE", "EF", "EG", "EH",
    "EI", "EJ",
    "EL",
    "ES",
    "EU", "EV", "EW",
    "F",
    "G", "GA", "GB", "GC", "GD", "GI", "GJ", "GM", "GN", "GO", "GP",
    "GQ", "GR", "GS", "GT", "GU", "GW", "GX",
    "HA", "HG",
    "HB", "HB0",
    "HV",
    "I", "IB", "IC", "ID", "IE", "IF", "IG", "IH", "II", "IJ", "IK",
    "IL", "IM", "IN", "IO", "IP", "IQ", "IR", "IS", "IT", "IU", "IV",
    "IW", "IX", "IY", "IZ",
    "LA", "LB", "LC", "LD", "LE", "LF", "LG", "LH", "LI", "LJ", "LK",
    "LL", "LM", "LN",
    "LX",
    "LY",
    "LZ",
    "OE",
    "OH", "OF", "OG", "OI", "OJ",
    "OH0",
    "OJ0",
    "OK", "OL",
    "OM",
    "ON", "OO", "OP", "OQ", "OR", "OS", "OT",
    "OX",
    "OY",
    "OZ",
    "PA", "PB", "PC", "PD", "PE", "PF", "PG", "PH", "PI",
    "S5",
    "SA", "SB", "SC", "SD", "SE", "SF", "SG", "SH", "SI", "SJ", "SK",
    "SL", "SM",
    "SN", "SO", "SP", "SQ", "SR",
    "SV", "SV5", "SV9", "SX",
    "TA", "TB", "TC",
    "TF",
    "TK",
    "UA", "UB", "UC", "UD", "UE", "UF", "UG",
    "UR", "US", "UT", "UU", "UV", "UW", "UX", "UY", "UZ",
    "UN", "UP", "UQ",
    "YL",
    "YO", "YP", "YQ", "YR",
    "YU", "YT",
    "Z3",
    "Z6",
    "ZA",
    "ZB",
    # Nordamerika
    "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AI", "AJ", "AK",
    "AL", "AM", "AN",
    "K", "KA", "KB", "KC", "KD", "KE", "KF", "KG", "KH", "KI", "KJ",
    "KK", "KL", "KM", "KN", "KO", "KP", "KQ", "KR", "KS", "KT",
    "KU", "KV", "KW", "KX", "KY", "KZ",
    "N", "NA", "NB", "NC", "ND", "NE", "NF", "NG", "NH", "NI", "NJ",
    "NK", "NL", "NM", "NN", "NO", "NP", "NQ", "NR", "NS", "NT",
    "NU", "NV", "NW", "NX", "NY", "NZ",
    "W", "WA", "WB", "WC", "WD", "WE", "WF", "WG", "WH", "WI", "WJ",
    "WK", "WL", "WM", "WN", "WO", "WP", "WQ", "WR", "WS", "WT",
    "WU", "WV", "WW", "WX", "WY", "WZ",
    "VE", "VA", "VB", "VC", "VD", "VF", "VG",
    "VO",
    "VY",
    "XE", "XF",
    # Südamerika
    "CE", "CA", "CB", "CC", "CD",
    "HC", "HD",
    "HI",
    "HK", "HJ",
    "HP",
    "HR",
    "LU", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9",
    "OA",
    "PY", "PP", "PQ", "PR", "PS", "PT", "PU", "PV", "PW", "PX",
    "TI", "TE",
    "YN",
    "YS",
    "YV", "YW",
    "ZP",
    "ZL", "ZK",
    # Afrika
    "5B",
    "5N", "5O",
    "5R", "5S",
    "5T",
    "5U",
    "5V",
    "5W",
    "5X",
    "5Y", "5Z",
    "6W",
    "7X",
    "9J",
    "9L",
    "9X",
    "CN",
    "D2", "D3",
    "E3",
    "ET",
    "J2",
    "J5",
    "TT",
    "TU",
    "V5",
    "ZS", "ZR", "ZT", "ZU",
    # Asien / Pazifik
    "4J", "4K",
    "4L",
    "4X", "4Z",
    "9M",
    "9V",
    "A4",
    "A6",
    "A7",
    "A9",
    "AP", "AQ",
    "B", "BA", "BD", "BG", "BH", "BI", "BJ", "BK", "BL", "BM", "BN",
    "BO", "BP", "BQ", "BR", "BS", "BT", "BU", "BV", "BW", "BX",
    "BY", "BZ",
    "DU", "DV", "DW", "DX", "DY", "DZ",
    "HL", "HM",
    "HS", "HT",
    "JA", "JB", "JC", "JD", "JE", "JF", "JG", "JH", "JI", "JJ", "JK",
    "JL", "JM", "JN", "JO", "JP", "JQ", "JR", "JS",
    "JT",
    "OD",
    "P5",
    "S2", "S3",
    "UK",
    "VK", "VH", "VI", "VJ",
    "VR",
    "VU", "VT",
    "XU",
    "XW",
    "XV",
    "XY", "XZ",
    "YB", "YC", "YD", "YE", "YF", "YG", "YH",
    "YI",
    "YK",
    "Z2",
})


def is_itu_prefix(part: str) -> bool:
    """Prüft ob 'part' ein bekannter ITU-Länderpräfix ist.

    Akzeptiert exakte Treffer (z. B. "DL", "5Z") und
    Präfix + eine abschließende Bezirksziffer (z. B. "5Z4", "SV9", "DL1").

    Zur Erweiterung: Präfix in PREFIXES aufnehmen.
    """
    s = part.upper()
    if s in PREFIXES:
        return True
    # Präfix + einzelne Bezirksziffer (z. B. "5Z4" → "5Z" ist Präfix, "4" Bezirk)
    if len(s) >= 2 and s[-1].isdigit() and s[:-1] in PREFIXES:
        return True
    return False
