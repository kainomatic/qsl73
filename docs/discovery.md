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

### Log-Tabelle: relevante Felder

| Spalte | Typ | Bedeutung |
|--------|-----|-----------|
| `callsign` | VARCHAR(50) NOCASE | Rufzeichen des Gegenübers |
| `qsodate` | DATETIME | QSO-Datum/-Zeit UTC (Format: `'2023-03-04 14:37:00Z'`) |
| `band` | VARCHAR(10) NOCASE | Band (z. B. `'10m'`, `'40m'`) |
| `mode` | VARCHAR(30) NOCASE | Betriebsart (z. B. `'SSB'`, `'FT8'`) |
| `qsoid` | VARCHAR(17) UNIQUE | Primärschlüssel, Zeitstempel-basiert (z. B. `'20230304145400760'`) |
| `stationcallsign` | VARCHAR(50) NOCASE | Eigenes Rufzeichen bei diesem QSO (z. B. `'DO6KBO'` bzw. `'DF1DS'`) |
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
| `S` | Sent: `"Yes"` / `"No"` — QSL von DF1DS abgeschickt? |
| `R` | Received: `"Yes"` / `"No"` — QSL von Gegenüber empfangen/bestätigt? |
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

QSOs, die **noch nicht** Papier-QSL-bestätigt sind:

```sql
-- in Python zu parsen, da SQLite-JSON-Funktionen nicht garantiert vorhanden:
-- Alle Rows laden, dann per json.loads() filtern:
-- entry["CT"] == "QSL" and entry["R"] == "No"  (oder kein QSL-Eintrag)
```

In der Testdatei: alle 428 QSOs sind noch nicht bestätigt.

### Schreibformat (was QSL73 schreiben soll)

Beim Markieren eines QSOs als „Papier-QSL bestätigt" ist das `qsoconfirmations`-JSON-Array zu aktualisieren:

**Vorher** (unbestätigt):
```json
{"CT":"QSL","S":"No","R":"No","SV":"Electronic","RV":"Electronic"}
```

**Nachher** (bestätigt, von QSL73 zu schreiben):
```json
{"CT":"QSL","S":"No","R":"Yes","SV":"Electronic","RV":"Electronic","RD":"2026-06-16T00:00:00Z"}
```

**Ableitung:** Basiert auf dem beobachteten LOTW-Muster bei `R="Yes"` + `RD`-Datumsfeld. In der Test-DB gibt es **keine** QSOs mit `CT="QSL", R="Yes"` — das ist der noch nie gesetzte Zustand. Das Schreibformat ist daher aus der analogen Struktur von LOTW/EQSL/QRZCOM abgeleitet.

**⚠️ Offene Frage (für Review):** Muss `RV` bei Papier-QSL auf `"Bureau"` oder `"Direct"` geändert werden (statt `"Electronic"`), oder akzeptiert Log4OM `"Electronic"` als Standardwert? Empfehlung: nach dem ersten echten Schreibvorgang prüfen, wie Log4OM die Anzeige interpretiert.

### Schreiboperation (Ablauf)

1. `qsoconfirmations` aus der DB lesen und per `json.loads()` parsen.
2. Eintrag mit `CT == "QSL"` suchen (immer vorhanden, da Log4OM alle 7 Typen anlegt).
3. `R` auf `"Yes"` setzen, `RD` auf aktuelles UTC-Datum in Format `"YYYY-MM-DDT00:00:00Z"`.
4. Array zurück in JSON serialisieren (`json.dumps()`).
5. Spalte `qsoconfirmations` per UPDATE in der SQLite-DB schreiben.

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

**Status: noch offen** — keine Test-QSL-Karten in Paperless-ngx verfügbar.

Ausstehend:
- OCR-Textqualität bei gedruckten vs. handschriftlichen QSL-Karten
- Aufbau Vorder-/Rückseite (zweiseitiges PDF)
- Bild-Endpunkte: `preview/`, `download/`, `thumb/`
- API-Paginierung bei Tag-Filter `qsl-card`

→ Wird nachgepflegt, sobald echte Karten in Paperless vorhanden sind.

---

## 6. Offene Fragen / Klärungsbedarfe

| # | Frage | Priorität |
|---|-------|-----------|
| 1 | `RV`-Wert bei bestätigtem Papier-QSL: `"Electronic"` beibehalten oder `"Bureau"` / `"Direct"` setzen? | **Hoch** (vor Schreiblogik klären) |
| 2 | Muss `S` auf `"Yes"` gesetzt werden (= QSL wurde abgeschickt), wenn Karte empfangen wird? | Mittel |
| 3 | Verhalten bei QSOs ohne `CT="QSL"`-Eintrag (ältere DB-Versionen)? | Niedrig |
| 4 | OCR-Qualität und Paperless-API-Details | Mittel (sobald Karten vorhanden) |
