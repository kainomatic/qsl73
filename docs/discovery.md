# QSL73 – Discovery-Befunde (Schritt 0)

> Alle Erkenntnisse basieren auf **read-only-Analyse** der Arbeitskopie  
> `TESTDB_DF1DS_Mai24_backup.sqlite` (Log4OM2 v0.6, DB Version 1, 428 QSOs).  
> Original-SHA256: `8f96afe5ade88c358a9fe3496e27e39377d24c2b58d55a6f28e6e8eb48e6a8fc` – unverändert bestätigt.

---

## 1. Datenbank-Schema

### Tabellen

Die DB enthält genau **2 Tabellen**:

| Tabelle | Zweck |
|---------|-------|
| `Informations` | Metadaten der DB-Instanz (Programmname, -version, DB-Version) |
| `Log` | Alle QSOs (428 Einträge in der Testdatei) |

**Informations-Eintrag:**
```
ProgramName = 'LOG4OM2', ProgramVersion = '0.6', DBVersion = 1
```

**Nachtrag 2026-09-19 (Anlass Issue #42, Handtest DF1DS):** An
`docs/testdateien/TESTDB_DH3KR_schreibtest.sqlite` migrierte eine neuere
Log4OM-Version die DB beim Laden von `DBVersion 1` auf `DBVersion 3`; die
`Log`-Tabelle hat danach **98 statt 97 Spalten** (neue Spalten u. a. `Region`,
`MUFDay`, `Reliability`, `SignalToNoiseRatio`, `Sunspots` — propagationsbezogen).
Das `qsoconfirmations`-Format (§2/§7) ist davon unverändert. Reine
Discovery-Notiz — ob QSL73s `validate_schema` mit `DBVersion 3` sauber läuft,
ist ein separates, hier nicht behandeltes Thema. Der obige Befund (`DBVersion 1`,
97 Spalten) bleibt als ursprünglicher Stand der Original-Testdatei bestehen.

### Log-Tabelle: relevante Felder

| Spalte | Typ | Bedeutung |
|--------|-----|-----------|
| `callsign` | VARCHAR(50) NOCASE | Rufzeichen des Gegenübers |
| `qsodate` | DATETIME | QSO-Datum/-Zeit UTC (Format: `'2023-03-04 14:37:00Z'`) |
| `band` | VARCHAR(10) NOCASE | Band (z. B. `'10m'`, `'40m'`) |
| `mode` | VARCHAR(30) NOCASE | Betriebsart (z. B. `'SSB'`, `'FT8'`) |
| `qsoid` | VARCHAR(17) UNIQUE | Primärschlüssel, Zeitstempel-basiert (z. B. `'20230304145400760'`) |
| `stationcallsign` | VARCHAR(50) NOCASE | Eigenes Rufzeichen bei diesem QSO (z. B. `'DO6XXX'` bzw. `'DF1DS'`) |
| `qsoconfirmations` | NVARCHAR(3000) | JSON-Array aller QSL-Bestätigungstypen (siehe §2) |
| `qsoenddate` | DATETIME | QSO-Endzeit UTC |
| `ownercallsign` | VARCHAR(50) | Rufzeichen des Log-Inhabers |

**Primärschlüssel:** `(band, callsign, mode, qsodate)` — natürlicher 4-Feld-Schlüssel, kein Auto-Increment.

### Datumsformat

- `qsodate` / `qsoenddate`: `'YYYY-MM-DD HH:MM:SSZ'` (Leerzeichen statt `T`, Suffix `Z`)
  - Beispiel: `'2023-03-04 14:37:00Z'`
- Datumsfelder **innerhalb** `qsoconfirmations` (SD/RD): ISO 8601 mit `T`
  - Beispiel: `'2023-03-26T00:00:00Z'`
- Hinweis: Beide Formate enthalten UTC, aber mit unterschiedlichem Trennzeichen.

---

## 2. QSL-Bestätigungsfeld: `qsoconfirmations`

### Struktur

`qsoconfirmations` ist ein **JSON-Array** (als TEXT gespeichert). Jedes QSO trägt typischerweise 7 Einträge, einen pro Bestätigungstyp:

```json
[
  {"CT":"QSL",     "S":"No",  "R":"No",  "SV":"Electronic", "RV":"Electronic"},
  {"CT":"EQSL",    "S":"Yes", "R":"No",  "SV":"Electronic", "RV":"Electronic", "SD":"2023-03-26T00:00:00Z"},
  {"CT":"LOTW",    "S":"Yes", "R":"Yes", "SV":"Electronic", "RV":"Electronic", "SD":"2023-03-04T00:00:00Z", "RD":"2023-03-19T00:00:00Z"},
  {"CT":"QRZCOM",  "S":"Yes", "R":"Yes", "SV":"Electronic", "RV":"Electronic", "RD":"2023-10-13T00:00:00Z"},
  {"CT":"HAMQTH",  "S":"No",  "R":"No",  "SV":"Electronic", "RV":"Electronic"},
  {"CT":"HRDLOG",  "S":"No",  "R":"No",  "SV":"Electronic", "RV":"Electronic"},
  {"CT":"CLUBLOG", "S":"No",  "R":"No",  "SV":"Electronic", "RV":"Electronic"}
]
```

**Feldbezeichnungen:**

| Feld | Bedeutung |
|------|-----------|
| `CT` | Confirmation Type: `QSL`, `EQSL`, `LOTW`, `QRZCOM`, `HAMQTH`, `HRDLOG`, `CLUBLOG` |
| `S` | Sent: `"Yes"` / `"No"` — QSL von DF1DS abgeschickt? (weitere Werte → §7) |
| `R` | Received: `"Yes"` / `"No"` — QSL von Gegenüber empfangen/bestätigt? (weitere Werte → §7) |
| `SV` | Sent Via: `"Electronic"` (Standardwert; auch `"Bureau"` / `"Direct"` möglich) |
| `RV` | Received Via: `"Electronic"` (Standardwert) |
| `SD` | Sent Date (ISO 8601 UTC) — nur wenn S="Yes" |
| `RD` | Received Date (ISO 8601 UTC) — nur wenn R="Yes" |

---

## 3. „Papier-QSL bestätigt" — Bedeutung und Schreibformat

### Was bedeutet bestätigt?

**Papier-QSL bestätigt** = Eintrag mit `CT = "QSL"` und `R = "Yes"` im `qsoconfirmations`-Array.

- Klar abgegrenzt von eQSL (`CT="EQSL"`), LoTW (`CT="LOTW"`), QRZ (`CT="QRZCOM"`) — diese haben **eigene CT-Einträge** und werden von QSL73 **nicht** gelesen oder geschrieben.
- `qslmsg` und `qslvia` sind separate Freitextfelder ohne Auswirkung auf den Bestätigungsstatus.

### Vorfilter (zu verarbeitende QSOs)

QSOs, die **noch nicht** Papier-QSL-bestätigt sind (Kandidaten für QSL73):

| `R`-Wert | Bedeutung | Verhalten QSL73 |
|----------|-----------|-----------------|
| `"No"` | Offen, noch nicht bestätigt | **Kandidat** — bei Treffer auf `"Yes"` setzen |
| `"Requested"` | Karte wurde angefordert, noch nicht erhalten | **Kandidat** — bei Eingang und Treffer auf `"Yes"` setzen |
| `"Yes"` | Bereits bestätigt | **Überspringen** — nie als Kandidat anzeigen |
| `"Invalid"` | Sonderzustand (Log4OM-intern, Semantik unklar) | **Überspringen** — nicht anfassen, um keinen gesetzten Sonderzustand zu überschreiben |

```python
# Vorfilter in Python (SQLite-JSON-Funktionen nicht vorausgesetzt):
# entry["CT"] == "QSL" and entry["R"] in ("No", "Requested")
```

**Normalzustand der Test-DB:** Alle 463 QSOs haben `CT="QSL", R="No", RV="Electronic"`.
`"Requested"` und `"Invalid"` kommen in der Test-DB aktuell nicht vor, sind aber laut
Log4OM-UI (Dropdown: No / Requested / Yes / Invalid) mögliche Werte.

### Schreibformat — empirisch bestätigt (RV-Hand-Test, 2026-06-17)

Drei Test-QSOs wurden in Log4OM manuell als Papier-QSL bestätigt (je einmal
undefined, bureau, direct). Vorher/Nachher-Vergleich der DB-Kopie durch Claude Desktop.

**Vorher** (offen, unbestätigt) — Ausgangszustand aller Test-QSOs:
```json
{"CT":"QSL","S":"No","R":"No","SV":"Electronic","RV":"Electronic"}
```

**Nachher — je nach gewähltem Übertragungsweg:**

| Weg | Ergebnis-JSON |
|-----|---------------|
| Undefined | `{"CT":"QSL","S":"No","R":"Yes","SV":"Electronic"}` |
| Bureau | `{"CT":"QSL","S":"No","R":"Yes","SV":"Electronic","RV":"Bureau"}` |
| Direct | `{"CT":"QSL","S":"No","R":"Yes","SV":"Electronic","RV":"Direct"}` |

**Empirisch bewiesene Regeln** (maßgeblich für die Implementierung in Schritt 5):

| # | Regel | Befund |
|---|-------|--------|
| 1 | `R` | Wechselt `"No"` → `"Yes"`. Nie `"V"` (DXCC-Verifizierung bleibt dem Nutzer). |
| 2 | `RV` | `"Bureau"` / `"Direct"` (großer Anfangsbuchstabe). Bei **Undefined**: RV-Feld wird **ganz entfernt** (kein Wert `"Undefined"` geschrieben). Ein vorhandener RV-Wert (z. B. `"Electronic"`) wird dabei überschrieben bzw. entfernt. |
| 3 | `RD` | **Wird nicht geschrieben.** Die frühere Annahme (RD auf Bestätigungsdatum setzen) ist widerlegt. Log4OM schreibt kein Empfangsdatum für Papier-QSL. |
| 4 | `S`, `CT`, `SV` | Bleiben unverändert. Alle anderen Bestätigungstypen (EQSL, LOTW, QRZCOM, HAMQTH, HRDLOG, CLUBLOG) werden byte-genau nicht berührt. |

### Schreiboperation (Ablauf)

1. `qsoconfirmations` aus der DB lesen und per `json.loads()` parsen.
2. Eintrag mit `CT == "QSL"` suchen (immer vorhanden, da Log4OM alle 7 Typen anlegt).
3. `R` auf `"Yes"` setzen (nie `"V"`).
4. `RV` je nach `qsl_route_default` setzen: `"bureau"` → `"Bureau"`, `"direct"` → `"Direct"`,
   `"undefined"` → RV-Schlüssel aus dem Dict entfernen (falls vorhanden).
5. `RD` **nicht** setzen (kein Datum schreiben).
6. Array zurück in JSON serialisieren (`json.dumps()`).
7. Spalte `qsoconfirmations` per UPDATE in der SQLite-DB schreiben.

---

## 4. Feldmapping: QSO-Matching

| Matching-Feld | Log-Spalte | Besonderheit |
|---------------|------------|--------------|
| Rufzeichen | `callsign` | COLLATE NOCASE; Gegenüber, nicht eigenes |
| Datum/Zeit | `qsodate` | Format `'YYYY-MM-DD HH:MM:SSZ'` (UTC) |
| Band | `band` | COLLATE NOCASE; z. B. `'10m'` |
| Mode | `mode` | COLLATE NOCASE; z. B. `'SSB'`, `'FT8'` |

**Wichtig:** Der Primärschlüssel `(band, callsign, mode, qsodate)` stellt sicher, dass kein Duplikat entstehen kann. `qsoid` wird für den Update-Zugriff genutzt (eindeutig, schnell).

---

## 5. Paperless-ngx / OCR-Befund

### 5.1 Karten-Analyse (echte Karten, read-only durch Claude Desktop, 2026-06-16)

**Getestetes Material:** 2 echte QSL-Karten (DL0AAA-Sammlung).

**Befund QR-Code (moderne Karte, DARC-QSL-Service):**
- Karte trägt QR-Code mit sauberem, strukturiertem Klartext-Format:
  ```
  From: DK8XX  To: DL0AAA
  Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  Prop_Mode: TR  RST: -24  QSL: TNX
  ```
- Felder: `From` (Gegenstation), `To` (eigener Call), `Date`, `Time`, `Band`, `Mode`, `RST`.
- Datum-Format: `TT.MM.JJ` (zweistelliges Jahr).
- Liefert alle vier Match-Felder fehlerfrei — löst OCR-Probleme vollständig für diese Karten.

**Befund OCR (PDF-interne OCR, Sichtprüfung):**
- Gedruckte Karte (DK8XX): Band `"6m"` wurde von der OCR zu `"tToemvem"` zerstört.
  Tabellen-Layout wird im OCR-Textfluss zerrissen; andere Felder partiell erkennbar.
- Handschriftliche Karte (G7XXX, 1992): liefert kaum brauchbaren OCR-Text;
  Datum `"3/10/92"` (Format TT/MM/JJ, 2-stellig), handschriftliche Felder nicht erkannt.
- **Wichtig:** Die sichtgeprüfte OCR ist die **PDF-interne** OCR, NICHT die Paperless-OCR.
  QSL73 nutzt `GET /api/documents/{id}/?fields=content` (Paperless-OCR), die abweichen kann.
  Qualitätsvergleich Paperless-OCR vs. PDF-OCR: **live zu verifizieren (→ Issue #2)**.

**Normalisierungsbedarf (empirisch bestätigt):**
- Datum: `TT.MM.JJ`, `TT/MM/JJ` → ISO; Zweideutigkeit → „unsicher" statt falsch matchen.
- Band: Frequenzangabe oder Bandname; OCR fehleranfällig → Umrechnung + Fehlertoleranz nötig.
- Mode: ältere ITU-Bezeichnungen (`J3E` → SSB) vorhanden; Mapping-Tabelle nötig.
- From/To: explizit trennbar bei QR-Code; bei OCR schwieriger → eigener Call als Anker.

### 5.2 Paperless-API — Verifikationsbefund (Schritt 3b, 2026-06-16)

Real getestet gegen lokale Paperless-ngx-Docker-Instanz mit 7 echten QSL-Karten
(getaggt `qsl-card`). Client: `src/qsl73/paperless.py`.

#### Client-Funktionen (real nachgewiesen)

| Funktion | Ergebnis |
|----------|----------|
| `get_documents_by_tag("qsl-card")` | Alle 7 Karten gefunden; Paginierung funktioniert |
| `get_document_content(id)` | OCR-Text sofort verfügbar (0 s Wartezeit) |
| `get_document_preview(id)` | PDF-Bytes (400–860 KB je Karte) |
| `get_document_download(id)` | PDF-Bytes (identisch mit preview) |
| `get_document_thumb(id)` | WebP-Bytes (10–45 KB) |
| `add_tag_to_document` | Test-Tag hinzugefügt; `qsl-card` bleibt erhalten ✅ |
| `remove_tag_from_document` | Test-Tag entfernt; `qsl-card` bleibt erhalten ✅ |

**Bildformate:** `preview` und `download` liefern beide das optimierte PDF (gleiche Byte-Größe).
`thumb` liefert WebP. Die Auflösung der PDFs (400–860 KB) ist für manuelle Ansicht ausreichend.

#### OCR-Qualitätsbefund (pro Kartentyp, anonymisiert)

7 Karten in 3 Typen:

**Typ A — Gedruckte Karte mit QR-Code (modernes DARC-Format, 1 Karte):**
- Paperless-OCR liefert lesbaren Tabellentext; Rufzeichen und Datum erkennbar.
- **Kritisch:** Band `6m` wird von Paperless-OCR als `tToemvem` ausgegeben — gleicher Fehler wie bei der PDF-internen OCR (bestätigt). Band-Feld nicht direkt verwertbar via OCR.
- **QR-Code-Inhalt ist NICHT im Paperless-OCR-Text enthalten.** Das strukturierte Format
  (`From: [CALL] To: [CALL] Date: TT.MM.JJ Time: HH:MM Band: 6m Mode: FT8 ...`)
  ist nur im Bild/PDF codiert — Paperless-OCR dekodiert QR-Codes nicht.
  QR-Matching erfordert client-seitiges QR-Decoding aus dem heruntergeladenen PDF.

**Typ B — Gedruckte Karte ohne QR (modernes und älteres Format, 3 Karten):**
- OCR-Qualität: mittel bis mäßig.
- Rufzeichen meist erkennbar. Datum im Format `TT.MM.JJ` oder `TT.MM.JJJJ` partiell erkennbar.
- Band/Mode-Felder: oft im Tabellenkontext, aber durch OCR-Artefakte unzuverlässig.
- Frequenzangabe statt Bandname kommt vor (z. B. `5,3570` statt `60m`/`6m` → Umrechnung nötig).
- Ein Beispiel mit lesbarem Datum+Frequenz+Mode bei modernem Kartenlayout:
  `26.04.25 19:52  5,3570  FT8` (anonymisiert; kein Rufzeichen wiedergegeben).
- Ältere gedruckte Karten (1990er, dichtes Layout): OCR-Text zerstückelt, Felder schwer trennbar.

**Typ C — Handschriftliche Karte (3 Karten: US-amerikanisch, britisch ~1990, französisch):**
- OCR-Qualität: schlecht bis sehr schlecht.
- Rufzeichen teils erkannt, teils verfälscht (z. B. Buchstabe verdoppelt/verdreht).
- Datum: Teilerkennung, Format inkonsistent (`TT/MM/JJ`, `TTMMM JJ`, kaum les­bar).
- Band/Mode: in handschriftlichen Tabellenzellen praktisch nicht zuverlässig erkennbar.
- **Fazit Typ C:** Auto-Matching über OCR allein nicht möglich.

#### Gesamtbewertung: Taugt Paperless-OCR für Auto-Matching?

**Nein — OCR allein ist nicht produktionstauglich für das automatische Matching.**

| Pfad | Machbarkeit | Anmerkung |
|------|-------------|-----------|
| QR-Code (Priorität 1) | Machbar, aber aufwändig | QR nicht in OCR; erfordert PDF-Download + QR-Decoder im Client |
| OCR-Matching (Priorität 2) | Nur für moderne gedruckte Karten, mit Normalisierung | Band-OCR unzuverlässig; handschriftliche Karten fallen durch |
| Manueller Pfad (Priorität 3) | Immer nötig als Fallback | Für handschriftliche und alte Karten dominant |

**Empfehlung (bestätigt):** Der im KONZEPT.md vorgesehene dreistufige Pfad ist korrekt:
QR → OCR (normalisiert) → manuell. Bei diesem Kartenset dominieren handschriftliche/alte
Karten, d. h. der manuelle Pfad wird im Alltag häufig genutzt.

**QR-Pfad (Schritt 4):** QR-Decoding muss im Client aus dem PDF-Bild erfolgen (z. B. `pyzbar`
oder `opencv` auf einem gerenderten PDF-Frame). Paperless-OCR ist kein Ersatz dafür.

### 5.3 Erweiterte Karten-Analyse (Claude Desktop, alle 7 Karten, 2026-06-16)

Vollständige Bilderkennung aller 7 Musterkarten (anonymisiert/zusammengefasst).

**Kartenverteilung:**
- 1× gedruckt mit QR-Code (DARC-QSL-Service, modernes Format)
- 2× gedruckt ohne QR (modernes und älteres Format, 1990er)
- 4× handschriftlich (US-amerikanisch, britisch ~1990, französisch, italienisch)

**Neue Befunde gegenüber §5.1/§5.2:**

| Befund | Detail |
|--------|--------|
| QR-Code ≠ QSO-Daten | Eine Karte (Zazzle-Druckdienst) trägt einen QR-Code mit Werbe-/Herstellerkennung, keinen QSO-Inhalten. QR-Inhalt muss vor Verwendung auf QSO-Format validiert werden. |
| Portabler eigener Call | Eine Karte adressiert den eigenen Call portabel (`SV9/[BASISCALL]`). Starrer Vergleich `To == own_callsign` würde scheitern. Basis-Call-Extraktion nötig. |
| Datum `TT Monatsname JJJJ` | Format `23Apr2025` auf gedruckter Karte — real und häufig genug für Unterstützung. |
| Datum US-Spaltenformat | Getrennte Tabellenfelder Month/Day/Year — auf US-Karte; zusammenzusetzen und zu normalisieren. |
| Datum exotisch (römisch) | Format `17-XI-93` (römische Monatsziffern) auf einer Karte — bewusst NICHT per Sonderregel erschlossen, da selten und fehlerträchtig. → unsicher. |
| Mode `2×SSB` | Auf französischer Karte; normalisiert zu SSB. |
| Daten auf Vorderseite | Eine Karte hatte die QSO-Tabelle auf der Vorderseite, nicht der Rückseite. Alle PDF-Seiten müssen ausgewertet werden. |

**Konsequenzen für §6 (bereits eingearbeitet in KONZEPT.md):**
- §6.2: QR-Inhalt validieren; mehrere QR-Codes pro Karte möglich; alle Seiten durchsuchen.
- §6.3: Tolerantes eigenes-Call-Matching; erweiterte Datum-Tabelle; `2×SSB`→SSB; alle Seiten.
- Grundsatz: unbekannte Formate → unsicher, kein Ratespiel.

### 5.4 Rufzeichen-Vielfalt in der Test-DB (anonymisiert, 2026-06-16)

Analyse der echten Test-DB (428 QSOs, 403 eindeutige Gegenstationen):

**Gegenstationen mit `/`-Zusatz (10 von 403):**
- Suffixe: `/P` (6×), `/QRP` (1×) — bekannte Portabel-/Betriebsart-Kürzel.
- Präfixe: 2× Karten mit Länderpräfix + `/` + Stammrufzeichen (Gast-Operation).
- Grenzfall: 1× `[CALL]/IF9` — Region/Distriktsuffix, nicht eindeutig einem bekannten
  Suffix zuzuordnen (→ Fall c der Stammrufzeichen-Zerlegung: unsicher).

**Eigene Rufzeichen (`stationcallsign`):**
- Drei verschiedene `stationcallsign`-Werte in der DB (zwei feste Calls, einer portabel mit `/P`-Suffix).
- Der Nutzer hat also unter mehreren eigenen Calls geloggt. Ein starrer Vergleich nur
  gegen `own_callsign` würde portabel adressierte Karten verwerfen.
- → Bestätigt die Entscheidung: `To`-Abgleich gegen `own_callsign` UND alle
  `stationcallsign`-Werte der DB (mit Stammrufzeichen-Toleranz). → ADR-0013.

## 6. Offene Fragen / Klärungsbedarfe

| # | Frage | Status |
|---|-------|--------|
| 1 | `RV`-Wert bei bestätigtem Papier-QSL: welche Werte schreibt Log4OM exakt (Groß-/Kleinschreibung, akzeptiert Log4OM `"Undefined"`?) | **Erledigt** → RV-Hand-Test 2026-06-17; exaktes Format in §3 dokumentiert (→ ADR-0005/0006 aktualisiert) |
| 2 | Muss `S` auf `"Yes"` gesetzt werden, wenn Karte empfangen wird? | **Entschieden:** Nein — `S`/`SV` bleiben unverändert; QSL73 bestätigt nur Empfang |
| 3 | Verhalten bei QSOs ohne `CT="QSL"`-Eintrag (ältere DB-Versionen)? | **Aufgelöst** (Issue #4, 2026-09-17) → siehe Absatz unten |
| 4 | OCR-Qualität (Paperless-OCR) und Paperless-API-Details | **Erledigt** → §5.2/§5.3 (Schritt 3b) |
| 5 | `R`-Wert `"V"` (DXCC-verifiziert) vs. `"Yes"`: setzt QSL73 „V"? | **Entschieden:** Nein — QSL73 setzt ausschließlich `"Yes"`. `"V"` vergibt der Nutzer selbst im Award-Checker. |
| 6 | Exakte Strings für `Queued`/`Invalid`/`Requested` je Seite (S/R) + Verhalten beim tatsächlichen Upload zu einem Dienst (welche Felder ändern sich, wird `SD` gesetzt?) | **Weitgehend erledigt** → Handtest DF1DS 2026-09-19 (Issue #42): `Requested`/`Queued`/`Invalid` exakt gesichert, siehe §7. **Weiterhin offen:** Verhalten beim tatsächlichen Upload zu einem Dienst (welche Felder ändern sich, wird `SD` gesetzt?) — in DF1DS' Setup nicht durchführbar. |

### 6.1 Auflösung Frage #3 — QSOs ohne `CT="QSL"`-Eintrag (Issue #4)

Der Randfall ist durch drei ineinandergreifende Sicherheitsebenen abgedeckt — kein
Code-Fix nötig, kein stilles Neuanlegen eines QSL-Eintrags:

1. **`apply_paper_qsl` wirft `QslEntryNotFoundError`** statt still einen neuen Eintrag
   anzulegen oder einen anderen Eintragstyp zu überschreiben (ADR-0019).
2. **`log4om_db.validate_schema`** erkennt den Fall vorgelagert per Stichprobe (erste
   bis zu 30 Zeilen mit `qsoconfirmations`) und liefert eine klare deutsche Meldung,
   bevor überhaupt ein Backup oder eine Transaktion beginnt. `write_confirmations`
   ruft `validate_schema` als allerersten Schritt auf → bei Abweichung `SchemaError`,
   kein Schreibversuch.
3. **Transaktions-Rollback als zweite Verteidigungslinie:** Besteht die Stichprobe
   (weil andere Zeilen einen gültigen QSL-Eintrag haben), aber eine einzelne Karte
   innerhalb der Transaktion hat keinen `CT="QSL"`-Eintrag, wirft `_run_transaction`
   `QslEntryNotFoundError` → ROLLBACK des gesamten Schreibvorgangs, kein Teilschreiben.

**Bewusst akzeptierte Einschränkung (Stichprobe):** `validate_schema` prüft nur eine
Stichprobe (bis zu 30 Zeilen), nicht die gesamte Tabelle. In einer **gemischten DB** —
die meisten QSOs haben einen QSL-Eintrag, einzelne ADIF-importierte nicht — besteht die
DB die Schema-Prüfung (sobald irgendeine Zeile der Stichprobe einen gültigen Eintrag
hat), und eine betroffene Einzelkarte fällt dann erst in der Transaktion als
`QslEntryNotFoundError` auf → ROLLBACK des gesamten Schreibvorgangs. Das ist **sicher**
(nichts Falsches wird geschrieben, kein Datenverlust), aber die Nutzermeldung ist dann
die technische Rollback-Meldung statt einer kartenspezifischen Meldung vorab. Bewusst so
belassen (DF1DS-Entscheidung, 2026-09-17), da der Fall bei normalen Log4OM-QSOs praktisch
nicht auftritt (Issue-Priorität niedrig). Optionaler künftiger Feinschliff (kartenspezifische
Nutzermeldung statt Rollback-Meldung) bei Bedarf als separates Issue.

---

## 7. Nachtrag 2026-09: weitere Log-Tabellen- und `qsoconfirmations`-Befunde (Anlass Issue #42)

Read-only an einer Test-DB-Kopie erhoben, im Rahmen der Planung von Issue #42
(Werkzeug „Bestätigungsübersicht"). Kein Code-Bezug — reine Discovery-Ergänzung.

- **Log-Tabelle:** 97 Spalten. Voll gefüllt und filtertauglich: `dxcc`, `country`, `cont`,
  `cqzone`, `ituzone`, `pfx`, `freq`, `distance`, `stationcallsign`. Teilweise gefüllt:
  `gridsquare`, `contestid`, `qslvia`, `state`.
- **`contactreferences`:** JSON-Array mit Award-Referenzen (Schlüssel `AC`; beobachtet u. a.
  DXCC, WAZ, WPX, WAC, WAE, VUCC, IOTA, POTA, SOTA).
- **`S` kennt zusätzlich `"Requested"`** (bei `CT="EQSL"` beobachtet). Laut Log4OM-Forum
  bietet der QSL-Manager außerdem `"Queued"` und `"Invalid"` an — in der Test-DB **nicht**
  vorgekommen, daher **offen**: exakte Schreibweise noch nicht per Handtest gesichert
  (Handtest laut Issue #42 ausstehend, siehe §6, Frage #6).
- **ADIF-Hintergrund der Werte** (Log4OM leitet sie davon ab): `RCVD=Requested` = die
  loggende Station (DF1DS) hat eine QSL angefordert; `SENT=Requested` = die Gegenstation
  hat eine QSL angefordert; `SENT=Queued` = zum Versand/Upload ausgewählt. Hinweis: Bei
  elektronischen Diensten ist `"Requested"` in Log4OM oft nur der konfigurierte
  Standardwert neuer QSOs, keine bewusste Nutzeraktion — die Bedeutung ist daher
  kontextabhängig, nicht eindeutig interpretierbar.
- **Zusatzschlüssel `EXT`** im `CT="HRDLOG"`-Eintrag: enthält ein ADIF-Schnipsel (u. a. mit
  Rufzeichen) — Struktur notiert, Inhalt hier bewusst nicht wiedergegeben (ADR-0050, keine
  echten fremden Rufzeichen im Repo).
- **SD/RD:** bei elektronischen Diensten vorhanden; für Papier-QSL (`CT="QSL"`) schreibt
  Log4OM kein `RD` (bestätigt konsistent mit §3).

### 7.1 Nachtrag 2026-09-19: Handtest `Requested`/`Queued`/`Invalid` (Issue #42)

Read-only-Auswertung durch Claude Desktop an `docs/testdateien/TESTDB_DH3KR_schreibtest.sqlite`,
nachdem DF1DS vier Test-QSOs im Log4OM-QSL-Manager gesetzt hat. Löst den in §6 Frage #6
offenen Teil (exakte Strings) weitgehend auf.

**Ausgangszustand aller vier QSL-Blöcke vorher:**
```json
{"CT":"QSL","S":"No","R":"No","SV":"Electronic","RV":"Electronic"}
```

**Nachher, je Testfall:**

| Fall | qsoid | Aktion in Log4OM | QSL-Block nachher |
|---|---|---|---|
| Papier EMPFANGEN = angefordert | `20250426195200002` (DG5MLA) | R auf „angefordert" | `{"CT":"QSL","S":"No","R":"Requested"}` |
| Papier GESENDET = angefordert | `20250423122300001` (OE6DRG) | S auf „angefordert" | `{"CT":"QSL","S":"Requested","R":"No"}` |
| Papier GESENDET = vorgemerkt | `20250402194200003` (DK8NE, 19:42) | S auf „vorgemerkt" | `{"CT":"QSL","S":"Queued","R":"No"}` |
| Dienst auf ungültig | `20250402090000004` (DK8NE, 09:00, LOTW) | S und R auf „ungültig" | `{"CT":"LOTW","S":"Invalid","R":"Invalid","SV":"Electronic","RV":"Electronic"}` |

Wörtliche Schreibweise (exakte Groß-/Kleinschreibung): `"Requested"`, `"Queued"`
(großes Q — dieser Wert kam in keiner der bisherigen Test-DBs vor, jetzt erstmals
empirisch gesichert), `"Invalid"` (großes I).

**Zusatzbefunde:**

1. Bei `"Requested"`/`"Queued"` **entfernt** Log4OM die Felder `SV` und `RV` aus dem
   QSL-Block (siehe Fälle „angefordert"/„vorgemerkt" oben: nur noch `CT`/`S`/`R`). Bei
   `"Invalid"` bleiben `SV`/`RV` erhalten (Fall „Dienst auf ungültig"). Konsequenz für
   Issue #42: Das Logikmodul darf nicht voraussetzen, dass `SV`/`RV` in jedem Block
   vorhanden sind — fehlende Felder sind normal.
2. `"Invalid"` wurde im Handtest auf **beiden** Seiten (S und R) gesetzt — das war eine
   bewusste manuelle Eingabe von DF1DS, kein beobachteter Log4OM-Automatismus. Ob Log4OM
   beim Setzen einer Seite die andere automatisch mitzieht, wurde nicht geprüft.
3. **Weiterhin offen:** Der Upload-Fall (welche Felder ändern sich beim tatsächlichen
   Upload zu einem Dienst, wird `SD` gesetzt?) wurde nicht getestet (in DF1DS' Setup
   nicht durchführbar) — bleibt der einzige noch offene Teil von Frage #6 (§6).

Keine Interpretation der Merker-Bedeutung enthalten (bewusst nicht Ziel dieses Handtests,
Issue #42 Grundentscheidung 3). Nebenbefund zur DB-Migration (DBVersion 3, 98 Spalten)
siehe §1-Nachtrag.
