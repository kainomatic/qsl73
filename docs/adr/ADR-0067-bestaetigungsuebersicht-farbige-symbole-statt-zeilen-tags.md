# ADR-0067: Bestätigungsübersicht — farbige Unicode-Symbole statt `tree.tag_configure`

**Status:** Accepted

## Kontext

Issue #42 (Auftrag 2) verlangt für die Bestätigungsübersicht „farbige Symbole" je
Dienstspalte: grün für bekommen, neutral/blau für gesendet, grau für keins, ein
gedämpftes Sondersymbol für Invalid — als Vorbild wurde `tree.tag_configure` aus dem
Hauptfenster genannt (`_tree.tag_configure("certain", foreground=...)` u. a.,
`gui/main_window.py`).

`tree.tag_configure` färbt jedoch nur ganze **Zeilen** (Item-Tags gelten für die
gesamte Zeile, nicht für einzelne Zellen). Die Bestätigungsübersicht zeigt aber pro
QSO-Zeile bis zu sieben Dienstspalten (QSL/LoTW/eQSL/QRZ/Clublog/HRDLog/HamQTH) mit
potenziell **unterschiedlichem** Zustand je Spalte — eine Zeile kann gleichzeitig
„bei LoTW bekommen" (grün) und „bei eQSL offen" (grau) zeigen. `ttk.Treeview` bietet
dafür keine Cell-Tags; individuelle Zellfarben sind ohne Custom-Drawing (Canvas statt
Treeview) nicht vorgesehen.

## Entscheidung

Die Bestätigungsübersicht kodiert Farbe direkt im **Zellinhalt** über farbige
Unicode-Symbole (Emoji-Glyphen, die in Windows/Segoe UI Emoji unabhängig von der
Widget-Vordergrundfarbe mit eigener Farbe gerendert werden), statt über
`tree.tag_configure`:

| Zustand (`ConfirmationState`) | Symbol | Farbe (glyphenintern) |
|---|---|---|
| `RECEIVED` (R=Yes) | `✅` | grün |
| `SENT` (S=Yes, noch nicht bekommen) | `⬆️` | farbig blau (Pfeil-Emoji) |
| `NONE` (keins von beiden) | `–` | neutral (Textfarbe) |
| `INVALID` | `⊘` | gedämpft (Textfarbe, eigene Form statt eigener Farbe) |

Zusätzlich eine kleine Uhr `🕐` als Suffix, wenn `has_marker()` True ist
(Requested/Queued auf Sende- oder Empfangsseite) — unabhängig vom Hauptzustand.

**Nachtrag (Nachbesserung Issue #42, 2026-09-19):** Der Merker-Suffix war
ursprünglich ein Punkt `·` — auf Rückmeldung von DF1DS zu blass/unauffällig, um als
eigenständiges Signal wahrgenommen zu werden. Ersetzt durch `🕐` (`MARKER_SUFFIX` in
`gui/confirmations_view.py`); Hauptsymbole (`✅`/`⬆️`/`–`/`⊘`) unverändert. Gleicher
Zeitpunkt: Die Kennzahlen wechselten von einer Textzeile (`format_metrics_line`) zu
Kachel-Widgets (`METRIC_TILE_LABELS`/`metric_tile_values`) — reine Darstellungsfrage,
keine neue Design-Entscheidung, da weiterhin nur harte Fakten gezeigt werden.

Implementiert in `gui/confirmations_view.py` (`cell_symbol`, `cell_display`) — tk-frei
und unit-getestet. Das Fenster (`gui/confirmations_window.py`) wendet die Symbole nur
als Zellwerte an; keine `tag_configure`-Zeilenfärbung für die Dienstspalten.

`Invalid` ist bewusst über die **Form** (`⊘` statt `–`), nicht nur über Farbe von
„keins" unterschieden — funktioniert auch, falls ein Nutzer den Emoji-Font-Rendering-
Unterschied nicht wahrnimmt (z. B. Fallback auf einfarbige Symbol-Fonts).

## Konsequenzen

**Positiv:**
- „Farbige Symbole" (Grundentscheidung aus Issue #42) technisch umsetzbar, ohne
  Custom-Canvas-Rendering oder eine Zeile pro Dienst.
- Zustand bleibt auch ohne Farbwahrnehmung (Graustufen-Monitor, Farbfehlsichtigkeit)
  über die Symbolform erkennbar (`✅`/`⬆️`/`–`/`⊘` sind alle unterschiedlich geformt).
- Zustand→Symbol-Mapping ist eine reine, tk-freie Funktion — unit-testbar ohne
  Display (Bezug #40/ADR-0062).

**Negativ / bewusst akzeptiert:**
- Emoji-Rendering hängt vom installierten System-Emoji-Font ab (Segoe UI Emoji unter
  Windows 10/11 Standard) — auf einem System ohne Farb-Emoji-Font fallen die Symbole
  auf einfarbige Glyphen zurück; die Bedeutung bleibt über die Form erhalten.
- Dieses Muster weicht von `tree.tag_configure` ab und ist damit kein Ersatz für die
  bestehende zeilenweite Färbung im Hauptfenster (dort bleibt ein Zustand pro Zeile
  gültig, `tag_configure` bleibt dort das richtige Werkzeug).
- Künftige Fenster mit ähnlichem Mehrfach-Zustand-pro-Zeile-Bedarf (mehrere
  unabhängige Spalten-Zustände) sollten dieses Muster (farbige Symbol-Glyphen als
  Zellwert) statt `tag_configure` wiederverwenden.

## Bezug

- Issue #42 (Fensteraufbau, Zell-Darstellung)
- ADR-0066 (Datenmodell: `ConfirmationState`, `has_marker`)
- ADR-0052 (Klick-Sortierung, hier auf Dienstspalten erweitert)
- ADR-0047 (Hover-Tooltips — Zell-Tooltip in `confirmations_window.py` nutzt
  dieselbe Optik, aber eine eigene Motion-getriebene Positionierung, da
  `attach_tooltip` nur ein Enter/Leave pro ganzem Widget kennt, nicht pro Zelle)
