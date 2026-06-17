# Realtest-Befunde — 2026-06-17 (Win10, erster echter Programmstart)

Erster Start von QSL73 auf echtem Windows 10 (Log4OM-Rechner) aus dem Quellcode
(`py -m qsl73`, dev-Branch). Paperless-Testinstanz über VPN (192.168.44.9:8000),
Log4OM-DB als Kopie, 7 Muster-QSL-Karten (an DH3KR) in Paperless.
Zweck: Verifikation der Schreib-/Nebenläufigkeitslogik gegen echtes Log4OM (Issue #8).

## Status
Programm startet und läuft grundsätzlich (Setup-Assistent, Hauptfenster, Lauf, Vorschau).
Der Realtest hat mehrere Umgebungs-/GUI-Bugs aufgedeckt, die in der Linux-CI unsichtbar waren.
Der eigentliche Schreib-Test gegen Log4OM (Issue #8, Szenarien A–D) steht noch aus, weil
vorher der QR-Pfad repariert werden musste (BUG-3).

## Bugs

### BUG-1 — pyproject.toml: build-backend ungültig
`build-backend = "setuptools.backends.legacy:build"` existiert nicht →
`pip install -e .` schlägt fehl mit `BackendUnavailable: Cannot import 'setuptools.backends.legacy'`.
Korrekt: `build-backend = "setuptools.build_meta"`.

### BUG-2 — pywin32 nicht automatisch installiert
pywin32 ist in requirements.txt auskommentiert; ohne es wirft crypto.get_default_backend()
CryptoUnavailableError beim Start. Musste manuell nachinstalliert werden.
Für Windows muss pywin32 verlässlich mitkommen (requirements bzw. Windows-Extra / Build).

### BUG-3 — QR-Paketname falsch (zxing-cpp statt zxingcpp) → QR-Pfad still tot  [WICHTIGSTER BEFUND]
Das QR-Decoder-Paket heißt auf PyPI **`zxing-cpp`** (mit Bindestrich), das Import-Modul
aber `zxingcpp` (ohne). In requirements.txt/Doku stand der Importname als Installationsname
(zudem auskommentiert) → `pip install zxingcpp` schlägt fehl (`No matching distribution found`).
Folge: zxing-cpp wird nie installiert, `_ZXING_OK = False`, `decode_qr_from_pdf` gibt für JEDE
Karte still `None` zurück → alle Karten fallen auf OCR, auch die DK8NE-QR-Karte; kein Hinweis
an den Nutzer (Import-Fehler in try/except still abgefangen; QR-Fehler nur `_log.debug`).
Im Realtest: alle 7 Karten "ocr" mit leeren Feldern → alle "unsicher".
Fix: in requirements.txt `zxing-cpp` (mit Bindestrich) als feste Windows-Abhängigkeit aufnehmen
(nicht auskommentiert). Verifiziert: `pip install zxing-cpp` liefert zxing-cpp-3.0.0
(cp312-Wheel) und funktioniert.
Zusatzbefund: Für Python 3.14 gab es (noch) kein zxing-cpp-Wheel → mit 3.12 getestet (s. ADR-0024).

### BUG-4 — Setup-Assistent: Passwort-Modus ohne Benutzername-Feld
Wenn Authentifizierung auf "password" gestellt wird, erscheint kein Benutzername-Feld; das
Fenster bleibt unverändert (zeigt weiter API-Token). Passwort-Login dadurch unmöglich.

### BUG-5 — Fortschrittsbalken läuft nach "Fertig" endlos weiter
Nach Abschluss des Laufs bleibt die indeterminate-Animation aktiv (kein `stop()` /
Moduswechsel). Optisch wirkt es, als liefe noch etwas.

### BUG-6 — Fehler/Diagnose werden still verschluckt (Logging fehlt)
QR-/Auswertungsfehler landen nur in `_log.debug` ohne sichtbares Log; fehlende QR-Verfügbarkeit
wird gar nicht gemeldet. Es gibt keine sichtbare Logdatei/Startdiagnose. Nutzer (und Entwickler)
sehen nicht, WARUM eine Karte nichts liefert. Beim Start sollte das Programm WARNEN, wenn die
QR-Funktion (zxing-cpp/pymupdf) nicht verfügbar ist, statt still auf OCR zu degradieren.
(Verwandt mit Schritt 7 Logging/Reporting — relevanten Teil vorziehen.)

## Erwartetes Verhalten (kein Bug, zur Klarstellung)
Die handschriftlichen/fremdsprachigen Karten (I6LTP, TM2CIN, G7JVJ, WB1CLT) liefern aus
Paperless unstrukturierten OCR-Text ohne "Key: Value"-Beschriftung (z. B.
`V3/DHIKR IT -xX1-93 |/8.63 | 88 1558 | ...`). Die `_parse_ocr_text`-Logik (Regex auf
beschriftete Felder) kann das nicht parsen → Felder None → "unsicher". Das ist erwartet;
diese Karten gehören in den manuellen Zuordnungs-Bildschirm (Schritt 6c). Bestätigt die
frühere OCR-Analyse aus Schritt 3b. Nur Karten mit QR (z. B. DK8NE) oder sauber strukturiertem
OCR-Text sind automatisch auswertbar.

## UX-Verbesserungen Setup-Assistent
- Verbindungstest-Button für Paperless (URL+Token direkt prüfen) im Setup-Fenster.
- Fenster öffnet zu klein → muss scrollen; beim Start höher/passend dimensionieren.
- Sprechende Feldnamen + Fragezeichen-Tooltips (Hover) für ALLE Felder, insbesondere:
  - "QSL-Route-Default" → verständlicher Name (Übertragungsweg der Karte: Büro/Direkt/unbestimmt)
  - "Fuzzy-Matching" → erklären (Toleranz bei kleinen Rufzeichen-Lesefehlern)
  - "Sprache" → "Deutsch"/"Englisch" statt "de"/"en"; klarstellen: Sprache der Programmoberfläche
  - "Anzahl Backups" → erklären (Anzahl aufbewahrter DB-Sicherungen vor dem Schreiben)
  - Tags (Eingangs-/Bestätigt-/Unsicher-Tag) → erklären, wofür welcher Tag dient

## Python-Version (Entwicklung + Build) — als ADR-0024 festhalten
Entscheidung: Python **3.12** ist die hart gesetzte Referenzversion für Entwicklung und Build.
Begründung: stabile Wheels für zxing-cpp, pywin32, pymupdf vorhanden (3.14 scheiterte an
fehlendem zxing-cpp-Wheel). 3.12 wird bis ca. 2028 unterstützt. Konsequenz: Build (Schritt 9)
nutzt 3.12; bei künftigem Wechsel auf eine neuere Version vorher auf Breaking Changes UND
Wheel-Verfügbarkeit (zxing-cpp/pywin32) prüfen. Bis dahin nicht ändern.

## Erkenntnis für den Build (Schritt 9)
- Die zu bündelnde Python-Version muss verfügbare Wheels für zxing-cpp UND pywin32 haben
  (nicht blind die neueste; 3.14 scheitert an zxing-cpp). → Python 3.12 (ADR-0024).
- zxing-cpp + pywin32 MÜSSEN im Windows-Build fest enthalten sein (Bezug Issues #6/#7).
- Beim Start: Warnung, wenn QR-Funktion nicht verfügbar (siehe BUG-6).

## Positiv bestätigt
- Programm startet, Setup-Assistent + Hauptfenster funktionieren.
- Paperless-Verbindung über VPN funktioniert; alle 7 Karten werden geholt und ausgewertet.
- DPAPI-Tokenspeicherung funktioniert (nach pywin32-Installation).
- GUI-Threading sauber (kein Einfrieren).
- Falsch-Positiv-Schutz greift: leere/unklare Karten → "unsicher", nichts fälschlich "sicher".
