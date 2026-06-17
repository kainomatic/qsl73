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
Die handschriftlichen Karten (TM2CIN, WB1CLT) liefern aus Paperless OCR-Text mit zerstörten
Rufzeichen (Leerzeichen im Call bzw. OCR-Buchstabenverwechslung). Die token-basierte
Extraktion (ADR-0025, nachgeführt nach diesem Realtest) erkennt keinen eindeutigen Absender
→ `call_from = None` → UNCERTAIN → manueller Zuordnungs-Bildschirm. Das ist korrekt.

**Nachgeführte Verbesserung (ADR-0025):** Gedruckte Karten im Tabellenlayout (OE6DRG, DG5MLA)
sind durch die token-basierte OCR-Extraktion jetzt vollständig automatisch auswertbar. Die
sieben realen OCR-Texte dieses Realtests sind als Test-Fixtures in `tests/test_run.py`
aufgenommen. Handschriftliche und stark zerstörte Karten (G7JVJ teils, TM2CIN, WB1CLT)
verbleiben korrekt im manuellen Pfad.

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

---

## Schreibtest verifiziert (2026-06-18)

Erster vollständiger End-to-End-Schreibtest des Schreib-Pfades (Issue #8, Szenario B).
Basis: `TESTDB_DH3KR_schreibtest.sqlite` (Kopie der DF1DS-Test-DB + 4 künstliche DH3KR-QSOs).
Vergleich: Vor-Schreib-Backup vs. geschriebene DB, byte-genau durch Claude Desktop verifiziert
(467 QSOs gesamt).

### Byte-genau bestätigte Schreib-Befunde

**Korrektheit der JSON-Transformation:**
- `R` wechselt `No` → `Yes` bei exakt den 3 Treffern (OE6DRG, DG5MLA 60m, DK8NE 6m).
- `RV`-Feld bei `route=undefined` vollständig entfernt — kein Restwert, kein `"Undefined"`
  (discovery §3 / ADR-0005 real bestätigt).
- `S`, `CT`, `SV` unverändert bei allen geschriebenen QSOs.
- EQSL-Bestätigung bei DG5MLA byte-genau erhalten — die isolierte JSON-Manipulation aus
  ADR-0019 / `log4om_write.apply_paper_qsl` greift ausschließlich auf den CT='QSL'-Eintrag
  und lässt alle anderen Einträge unberührt (real bestätigt).

**Kollateral-Integrität:**
- Exakt 3 von 467 QSOs verändert; alle übrigen QSOs byte-genau unberührt.
- DK8NE 20m-QSO (Grenzfall) **nicht** bestätigt — Band-Disambiguierung wirkt auch beim
  tatsächlichen Schreiben (6m-QSO trifft, 20m widerspricht und wird ausgeschlossen).

**Sicherheitsschicht:**
- Vor-Schreib-Backup wurde automatisch angelegt (Schritt 5c / ADR-0020, real bestätigt).
- Nebenläufigkeitsschutz: zweiter Schreibversuch ohne Neu-Einlesen wirft korrekt
  `DatabaseChangedError` (5c / ADR-0008, real bestätigt; der erste Schreibvorgang hat den
  Fingerabdruck geändert — zweiter Versuch schlägt fehl wie erwartet).

**ADR-0013 (stationcallsign-Abgleich) real bestätigt:**
- DH3KR-Karten wurden als eigenes Log erkannt, obwohl `own_callsign = DF1DS` in der Config.
  Zugehörigkeitsprüfung über alle `stationcallsign`-Werte der DB funktioniert wie spezifiziert.
  Kein Config-Eingriff nötig.

### Offen

- Visuelle Bestätigung in Log4OM selbst: zeigt Log4OM die Papier-QSL bei den 3 QSOs korrekt
  als bestätigt an? — vom Nutzer (DF1DS) noch zu prüfen (Log4OM auf eigenem Rechner öffnen).

### Kleine UX-Befunde aus dem Schreibtest (Issues #17, #18)

Zwei kleinere Punkte, die beim Schreibtest aufgefallen sind und als Issues festgehalten wurden:

- **Issue #17 — Encoding-Problem im Schreiben-Dialog:** Im „Schreiben abgeschlossen"-Dialog
  (messagebox) erscheinen bei bestimmten Zählwerten (z. B. `übersprungen=0`) Sonderzeichen
  bzw. nicht-rendernde Zeichen. Encoding/Formatierung der messagebox prüfen.
- **Issue #18 — DatabaseChangedError benutzerfreundlich behandeln:** Nach erfolgreichem Schreiben
  führt ein versehentlicher zweiter Klick auf „Jetzt schreiben" zu einem Fehler-Dialog mit
  Traceback. Stattdessen sollte ein freundlicher Hinweis „Bitte neu einlesen" erscheinen;
  Liste/Buttons sollten ggf. automatisch zurückgesetzt werden.

## Positiv bestätigt
- Programm startet, Setup-Assistent + Hauptfenster funktionieren.
- Paperless-Verbindung über VPN funktioniert; alle 7 Karten werden geholt und ausgewertet.
- DPAPI-Tokenspeicherung funktioniert (nach pywin32-Installation).
- GUI-Threading sauber (kein Einfrieren).
- Falsch-Positiv-Schutz greift: leere/unklare Karten → "unsicher", nichts fälschlich "sicher".

### P1-Fix verifiziert (Frischtest 2026-06-17, Win10, venv)
- **Saubere venv-Installation** (`pip install -r requirements.txt` + `pip install -e .`) läuft
  ohne manuelle Eingriffe durch — kein manuelles Nachinstallieren, kein PYTHONPATH-Setzen.
- **zxing-cpp automatisch installiert** (via PEP-508-Marker) → QR-Pfad wieder aktiv.
  DK8NE-Karte wird über QR erkannt und als CERTAIN eingestuft (zuvor: still auf OCR gefallen).
- **Fortschrittsbalken stoppt** nach "Fertig" korrekt (BUG-5 / Issue #13 behoben).
