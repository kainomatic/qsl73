# ADR-0047: Hover-Tooltips als einziges UI-Hilfe-Muster (kein Fragezeichen-Icon)

**Status:** Accepted

## Kontext

QSL73 hat zunehmend erklärungsbedürftige Bedienelemente — Paperless-URL, Auth-Modus,
Tag-Felder, Fuzzy-Matching, Trefferlimit, QSL-Route-Default u. a. Nutzer ohne technisches
Hintergrundwissen brauchen kurze Hinweise direkt am Bedienelement, ohne extra Hilfe-Fenster
aufrufen zu müssen.

Zwei gebräuchliche Muster stehen zur Auswahl:

1. **Fragezeichen-Icons / Badge-Labels** neben Feldern (separates UI-Element, sichtbar immer)
2. **Hover-Tooltips** (erscheinen erst auf Mausbewegung über das Widget, kein visuelles Rauschen)

## Entscheidung

QSL73 verwendet ausschließlich **native Hover-Tooltips** als projektweites UI-Hilfe-Muster.

- Implementierung: `gui/tooltip.py` → `attach_tooltip(widget, text)` (wiederverwendbar,
  crash-sicher, 500 ms Verzögerung, randloses `overrideredirect`-Toplevel).
- Tooltip-Texte: als `_TT_*`-Modulkonstanten im jeweiligen Fenster-Modul
  (Lokalitätsprinzip, analog zu bestehenden `_LBL_*`/`_MSG_*`-Konstanten; i18n-bereit).
- Keine Fragezeichen-Icons, keine separaten Hilfe-Labels neben Feldern.
- Gilt für alle bestehenden und künftigen Fenster.

## Konsequenzen

**Positiv:**
- Kein visuelles Rauschen — Tooltips erscheinen nur auf Anfrage (Hover).
- Konsistentes Verhalten in der gesamten App (ein Mechanismus, eine Implementierung).
- Einfache Erweiterung: `attach_tooltip(widget, _TT_MEIN_FELD)` in neuen Fenstern.
- Texte als Konstanten sind i18n-ready (Step 1 von `_LBL_*` → gettext-Extraktion).

**Negativ:**
- Funktioniert nur mit Maus; Tastatur-Nutzer ohne Hover sehen die Hints nicht
  (akzeptabler Trade-off für eine Desktop-App, bei der Mausbedienung Standard ist).
- Tooltip-Fenster (`overrideredirect`) sind unter manchen Compositing-WMs auf Linux
  ggf. nicht sichtbar — kein Problem, da QSL73 ausschließlich Windows unterstützt.
