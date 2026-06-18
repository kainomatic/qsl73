# ADR-0029: UX der manuellen Zuordnung — editierbare DB-Dropdowns, Rückseite-zuerst, Datepicker

**Status:** Accepted

## Kontext

Nach dem ersten Realtest des `ManualAssignmentDialog` (Schritt 6c-2/6c-3) wurden drei
UX-Mängel identifiziert:

1. **Band/Mode als freies Textfeld:** Nutzer muss gültige Werte auswendig wissen. Bei
   Tipp-Fehler findet die Suche nichts, ohne klaren Hinweis warum.
2. **Bildanzeige nur erste Seite (Vorderseite):** QSO-Daten (Datum, Band, Mode, Rufzeichen
   des Absenders) stehen laut Discovery §5.3 häufig auf der Rückseite. Die erste Seite
   enthält oft nur die Bildmotive.
3. **Datum als freies Textfeld:** Kein Kalender-Unterstützung, kein Format-Hinweis — der
   Nutzer muss das ISO-Format `YYYY-MM-DD` kennen. Außerdem war die Auflösung (100 DPI)
   für handschriftliche Karten (Issue #19) zu niedrig.

## Entscheidungen

### Band und Mode: editierbares Dropdown (ttk.Combobox)

Band- und Mode-Eingabefelder werden durch `ttk.Combobox` (`state="normal"`, d. h.
editierbar) ersetzt. Die Vorschlagswerte (`values`) werden aus `self._candidates`
abgeleitet — nur die tatsächlich im Suchraum vorkommenden, normalisierten Werte
(`distinct_bands`, `distinct_modes` — tk-freie, testbare Hilfsfunktionen).

**Begründung:** Die Menge gültiger Suchbegriffe ist gleichzeitig der Suchraum. Werte,
die bei keinem Kandidaten vorkommen, liefern ohnehin keinen Treffer — sie führen den
Nutzer aber ins Leere. Dropdowns zeigen direkt, welche Werte zum Ergebnis führen.
Tippen bleibt erlaubt (Combobox `state="normal"`), da der Nutzer z. B. einen selten
vorkommenden Band/Mode ggf. trotzdem prüfen möchte.

Kein DB-Zugriff im Dialog — Werte stammen aus dem bereits im Speicher vorhandenen
`RunResult.candidates`. Das hält den Dialog zustandslos und testbar (ADR-0028).

### Bildanzeige: letzte Seite (Rückseite) zuerst; Blättern zwischen Seiten

`render_pdf_pages()` rendert alle Seiten (150 DPI statt 100 DPI — Issue #19).
Im Dialog wird standardmäßig die **letzte Seite** angezeigt (Index = `page_count - 1`).
Zwischen den Seiten kann per `◀`/`▶`-Buttons geblättert werden; das Fenster bleibt
kompakt (keine gestapelte Anzeige aller Seiten). Bei einseitigem PDF erscheint diese
eine Seite, die Buttons werden deaktiviert.

**Begründung:** Discovery §5.3 zeigt, dass QSO-Daten meist auf der Rückseite stehen.
Standardmäßig die Rückseite zu zeigen spart dem Nutzer einen Klick in jedem
Zuordnungs-Dialog-Aufruf. Die Auflösungserhöhung auf 150 DPI verbessert die
Lesbarkeit handschriftlicher Karten (Issue #19 schließt damit).

`render_pdf_first_page` bleibt als Abwärtskompatibilitäts-Wrapper erhalten (delegiert
intern an `render_pdf_pages`).

### Datum: tkcalendar DateEntry mit Fallback

Das Datum-Textfeld wird durch `tkcalendar.DateEntry` ersetzt
(`date_pattern="yyyy-MM-dd"` für ISO-kompatible Ausgabe). Bei fehlendem `tkcalendar`
(Import-Fehler) fällt der Dialog auf ein einfaches Textfeld zurück und loggt eine
WARNING — kein Absturz, Dialog öffnet immer.

**Begründung:** Der Kalender-Datepicker führt den Nutzer zu einem gültigen Datumsformat
und reduziert Tippfehler. Die Fallback-Strategie ist nötig, damit der Dialog auch in
Umgebungen ohne tkcalendar (z. B. beim Bundeln ohne explizite tkcalendar-Einbindung)
weiterhin öffnet.

`tkcalendar` wird als neue Abhängigkeit in `requirements.txt` aufgenommen. Beim
PyInstaller-Bundle (Schritt 9) muss die Bibliothek explizit eingeschlossen werden
(Hinweis in CHANGELOG und Bundle-Schritt 9 zu vermerken).

## Konsequenzen

**Positiv:**
- Band/Mode-Dropdown: Nutzer sieht sofort, welche Werte sinnvoll sind; keine
  Nulltreffer durch Tippfehler bei bekannten Werten.
- Rückseite zuerst: QSO-Daten sofort sichtbar; ein Klick gespart pro Zuordnung.
- Höhere DPI (150): handschriftliche Karten besser lesbar.
- Mehrseiten-Unterstützung: Issue #20 (Rückseite anzeigbar) mit umgesetzt.
- Datepicker: sauberes ISO-Format ohne Tipp-Aufwand.
- Fallback-Strategie: Dialog bleibt immer öffenbar.

**Negativ / Aufwand:**
- Neue Abhängigkeit `tkcalendar` (PyPI; reine Python-Lib, keine native DLL,
  PyInstaller-kompatibel — aber explizit beim Bundle einschließen).
- `render_pdf_pages` rendert alle Seiten beim Bildladen; bei sehr vielen Seiten
  (Mehrseiten-Scan-Dokument) könnte das bei sehr großen PDFs dauern. Im QSL-Kontext
  sind 1–2 Seiten der Normalfall.
- Dialog-Code etwas komplexer (Seitennavigation, Datepicker-Fallback).
