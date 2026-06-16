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

**Nachher** (bestätigt, von QSL73 zu schreiben — Design-Entscheidung, empirisch noch zu bestätigen):
```json
{"CT":"QSL","S":"No","R":"Yes","SV":"Electronic","RV":"<qsl_route_default>","RD":"2026-06-16T00:00:00Z"}
```

**Design-Entscheidungen (festgeschrieben, Quelle: KONZEPT.md §3.3/§9):**

| Feld | Wert | Begründung |
|------|------|------------|
| `R` | `"Yes"` | Papier-QSL empfangen/bestätigt. Nie `"V"` — das ist DXCC-Verifizierung durch den Nutzer selbst, setzt QSL73 nicht. |
| `RD` | `"YYYY-MM-DDT00:00:00Z"` | Bestätigungsdatum UTC, ISO 8601 mit `T`-Trenner (analog SD/RD anderer CT-Typen). |
| `RV` | Aus Config (`qsl_route_default`) | Pauschaler Standardwert: **Undefined** (Default), Bureau oder Direct. `"Electronic"` wird nicht angeboten — das ist der Weg für LOTW/eQSL, fachlich falsch für Papier. ADIF-Enum: Undefined/Bureau/Direct/Electronic (M=Manager nur Import). |
| `SV` | Unverändert beibehalten | QSL73 bestätigt Empfang, nicht den Versand. `S`/`SV` bleiben wie vorgefunden. |

**⚠️ Wartet auf Hand-Test:** Das exakte Format (insb. Groß-/Kleinschreibung von `RV`-Werten,
ob Log4OM `"Undefined"` sauber akzeptiert/anzeigt, ob weitere Felder gesetzt werden) ist
empirisch noch nicht bestätigt. Der Hand-Test durch DF1DS steht aus (Log4OM: 1–2 QSOs manuell
als Papier-QSL bestätigen, je einmal Bureau und Direct, optional Undefined; dann Kopie ziehen
und diesen Abschnitt aktualisieren).

**Ableitung (bis Hand-Test):** Basiert auf dem beobachteten LOTW-Muster bei `R="Yes"` + `RD`-Datumsfeld. In der Test-DB gibt es **keine** QSOs mit `CT="QSL", R="Yes"`.

### Schreiboperation (Ablauf)

1. `qsoconfirmations` aus der DB lesen und per `json.loads()` parsen.
2. Eintrag mit `CT == "QSL"` suchen (immer vorhanden, da Log4OM alle 7 Typen anlegt).
3. `R` auf `"Yes"` setzen (nie `"V"`); `RD` auf Bestätigungsdatum UTC (`"YYYY-MM-DDT00:00:00Z"`); `RV` auf konfigurierten `qsl_route_default`-Wert setzen.
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

### 5.1 Karten-Analyse (echte Karten, read-only durch Claude Desktop, 2026-06-16)

**Getestetes Material:** 2 echte QSL-Karten (DH3KR-Sammlung).

**Befund QR-Code (moderne Karte, DARC-QSL-Service):**
- Karte trägt QR-Code mit sauberem, strukturiertem Klartext-Format:
  ```
  From: DK8NE  To: DH3KR
  Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  Prop_Mode: TR  RST: -24  QSL: TNX
  ```
- Felder: `From` (Gegenstation), `To` (eigener Call), `Date`, `Time`, `Band`, `Mode`, `RST`.
- Datum-Format: `TT.MM.JJ` (zweistelliges Jahr).
- Liefert alle vier Match-Felder fehlerfrei — löst OCR-Probleme vollständig für diese Karten.

**Befund OCR (PDF-interne OCR, Sichtprüfung):**
- Gedruckte Karte (DK8NE): Band `"6m"` wurde von der OCR zu `"tToemvem"` zerstört.
  Tabellen-Layout wird im OCR-Textfluss zerrissen; andere Felder partiell erkennbar.
- Handschriftliche Karte (G7JVJ, 1992): liefert kaum brauchbaren OCR-Text;
  Datum `"3/10/92"` (Format TT/MM/JJ, 2-stellig), handschriftliche Felder nicht erkannt.
- **Wichtig:** Die sichtgeprüfte OCR ist die **PDF-interne** OCR, NICHT die Paperless-OCR.
  QSL73 nutzt `GET /api/documents/{id}/?fields=content` (Paperless-OCR), die abweichen kann.
  Qualitätsvergleich Paperless-OCR vs. PDF-OCR: **live zu verifizieren (→ Issue #2)**.

**Normalisierungsbedarf (empirisch bestätigt):**
- Datum: `TT.MM.JJ`, `TT/MM/JJ` → ISO; Zweideutigkeit → „unsicher" statt falsch matchen.
- Band: Frequenzangabe oder Bandname; OCR fehleranfällig → Umrechnung + Fehlertoleranz nötig.
- Mode: ältere ITU-Bezeichnungen (`J3E` → SSB) vorhanden; Mapping-Tabelle nötig.
- From/To: explizit trennbar bei QR-Code; bei OCR schwieriger → eigener Call als Anker.

### 5.2 Paperless-API (noch offen)

Ausstehend (wartet auf Karten mit Tag `qsl-card` in Paperless, → Issue #2):
- Paperless-OCR-Qualität im Vergleich zur PDF-internen OCR
- Aufbau Vorder-/Rückseite (wird als zweiseitiges PDF geliefert?)
- Bild-Endpunkte: `preview/`, `download/`, `thumb/`
- API-Paginierung bei Tag-Filter `qsl-card`

---

## 6. Offene Fragen / Klärungsbedarfe

| # | Frage | Status |
|---|-------|--------|
| 1 | `RV`-Wert bei bestätigtem Papier-QSL: welche Werte schreibt Log4OM exakt (Groß-/Kleinschreibung, akzeptiert Log4OM `"Undefined"`?) | **Wartet auf Hand-Test** durch DF1DS |
| 2 | Muss `S` auf `"Yes"` gesetzt werden, wenn Karte empfangen wird? | **Entschieden:** Nein — `S`/`SV` bleiben unverändert; QSL73 bestätigt nur Empfang |
| 3 | Verhalten bei QSOs ohne `CT="QSL"`-Eintrag (ältere DB-Versionen)? | Offen / Niedrig; →Schema-Validierung §3.3 fängt das ab |
| 4 | OCR-Qualität (Paperless-OCR) und Paperless-API-Details | Offen → Issue #2 (Karten in Paperless taggen) |
| 5 | `R`-Wert `"V"` (DXCC-verifiziert) vs. `"Yes"`: setzt QSL73 „V"? | **Entschieden:** Nein — QSL73 setzt ausschließlich `"Yes"`. `"V"` vergibt der Nutzer selbst im Award-Checker. |
