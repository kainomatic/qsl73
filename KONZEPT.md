# QSL73 – Technische Spezifikation (KONZEPT.md)

> Fachliche Referenz für die Entwicklung. Beschreibt **was** QSL73 können muss und
> **wie** es sich verhalten soll – nicht die zeitliche Bau-Reihenfolge (→ ROADMAP.md).
> Maintainer/Entwickler: **DF1DS** (GitHub: kainomatic). Sprache der App: DE (Default),
> EN umschaltbar. Lizenz: GPLv3.
> Schreibmodell: Vorschau + Bestaetigung (kein separater dry-run; siehe §5/§7).

---

## 1. Zweck & Überblick

QSL73 ist ein Windows-Desktop-Tool (installierbare .exe), das gescannte **QSL-Karten
aus Paperless-ngx** automatisch mit den **QSOs im Log4OM-Logbuch (SQLite)** abgleicht
und bei sicherem Treffer das QSO als **Papier-QSL bestätigt** markiert. Zweifelsfälle
löst der Nutzer über einen **manuellen Zuordnungs-Bildschirm** mit Kartenanzeige.

Kernprinzipien:
- **Datensicherheit zuerst:** kein Schreibvorgang ohne Absicherung (WAL + Vor-Backup,
  Transaktion, definierte Schreibreihenfolge).
- **Transparenz:** "telefoniert nicht nach Hause"; nur 3 mögliche Verbindungen.
- **Nutzerkontrolle:** jeder Lauf zeigt erst eine Vorschau der geplanten Aenderungen und
  schreibt nur nach ausdruecklicher Bestaetigung; unsichere Faelle landen beim Menschen.

---

## 2. Systemumgebung

- **OS:** Windows 10 und 11, 64-Bit. (XP/8.1 nicht unterstützt.)
- **Sprache/Runtime:** Python 3.11+ (64-Bit), gebündelt via PyInstaller.
- **Installationsziel:** `C:\Program Files\QSL73` (pro Maschine, Adminrechte bei Installation).
- **Nutzerdaten:** `%APPDATA%\QSL73\` (config.yaml, logs\, backups\). Die Beta-Variante
  nutzt `%APPDATA%\QSL73-Beta\` — vollständig getrennt, keine gemeinsamen Daten (→ §16).
- **Externe Abhängigkeiten:** Log4OM (SQLite-DB lokal), Paperless-ngx (REST-API, erreichbar).

---

## 3. Datenquellen & Schnittstellen

### 3.1 Log4OM (SQLite)
- Standard-SQLite-Datei, vom Nutzer im Setup als Pfad angegeben.
- Zugriff **read+write**, Verbindung im **WAL-Modus** öffnen (technische Absturzsicherheit).
- **Discovery erforderlich** (an echter DB-Kopie, read-only): exakte Tabelle/Spalten für
  QSO-Felder (Rufzeichen, Datum/Zeit UTC, Band, Mode) und insbesondere das Feld/den Wert,
  der **„Papier-QSL bestätigt"** bedeutet (vs. eQSL/LoTW/QRZ). Schreibformat für
  „manuell bestätigt" exakt ermitteln, bevor geschrieben wird.
- Warnung ausgeben, wenn die DB in einem Cloud-Sync-Ordner (Dropbox/OneDrive) liegt.

### 3.2 Paperless-ngx (REST-API)
- Basis-URL vom Nutzer (vollständig inkl. http/https).
- **Auth:** Token ODER Benutzer/Passwort. Bei User/PW holt das Tool selbst einen Token via
  `POST /api/token/` und speichert **nur den Token** (DPAPI-verschlüsselt). Passwort wird
  nicht dauerhaft gespeichert.
- **OCR-Text:** `GET /api/documents/{id}/?fields=content`.
- **Dokument-Liste/Filter:** nach Tag (`qsl-card`) abrufen, paginiert.
- **Karten-Bild:** `GET /api/documents/{id}/preview/` (inline), `/download/` (Original,
  höhere Auflösung), `/thumb/` (Vorschau). Mehrseitiges PDF (Vorder-/Rückseite) zum Anzeigen
  in Bilder rendern.
- **Tag setzen/entfernen:** über das Document-Update-Endpoint (PATCH der Tag-Liste).

### 3.3 Schema-Validierung (Schutz vor Log4OM-Strukturänderungen)

Log4OM-Interna (Tabelle `Log`, Spalte `qsoconfirmations` als JSON mit CT/R/RD/RV) sind
undokumentiert und können sich mit einem Log4OM-Update ändern. QSL73 darf dann **niemals
blind schreiben**.

- **Erwartetes Schema** ist in `docs/discovery.md` dokumentiert (maßgebliche Quelle für die
  Implementierung).
- **Schema-Check beim Start** und **direkt vor jedem Schreibvorgang:** Tabelle `Log`
  vorhanden? Spalte `qsoconfirmations` vorhanden? JSON parsebar und CT/R/RD/RV wie erwartet?
- **Bei Abweichung:** Schreiben gesperrt; Lesen/Anzeigen soweit möglich weiter erlaubt.
  Klare Meldung: „Struktur der Log4OM-DB weicht vom erwarteten Format ab (evtl. Log4OM-
  Update). QSL73 schreibt aus Sicherheitsgründen nicht. Bitte auf aktualisierte QSL73-
  Version prüfen."
- **Lesezugriff defensiv:** fehlende Tabelle oder Spalte → definierter Fehlerfall mit
  verständlicher Meldung (kein Absturz); Diagnose-Log (`qsl73.log`) vermerkt exakt, was
  abweicht.
- **Abgrenzung zu §7:** §7 schützt vor DATEN-Änderungen während eines laufenden Durchgangs;
  §3.3 schützt vor STRUKTUR-Änderungen durch Log4OM-Updates.

**Akzeptanzkriterien:**
- Umbenannte oder fehlende Tabelle/Spalte → Schreiben gesperrt, Meldung angezeigt, kein Crash.
- Nicht-parsebares `qsoconfirmations`-JSON → Schreiben gesperrt + Eintrag in `qsl73.log`.
- Intaktes, bekanntes Schema → normaler Betrieb ohne Verzögerung.

---

## 4. Konfiguration & Sicherheit

- Config-Datei: `%APPDATA%\QSL73\config.yaml`. Enthält: Paperless-URL, Auth-Modus,
  (verschluesselten) Token, Log4OM-DB-Pfad, Tag-Namen, Fuzzy an/aus, QSL-Route-Default (RV),
  Sprache, Update-Check an/aus, Backup-Anzahl.
- **Token-Verschlüsselung:** Windows DPAPI (an Windows-Login gebunden), niemals Klartext.
- `config.example.yaml` als Vorlage im Repo; echte Config nie ins Repo (`.gitignore`).
- **Config-Migration:** beim ersten Start nach einem Update Pflicht – alte Config sauber
  auf neues Schema heben, mit Versionsfeld in der Config.

**Akzeptanzkriterien:**
- Frischer Start ohne Config → Setup-Assistent.
- Token liegt nur verschlüsselt vor (per Inspektion der config.yaml prüfbar).
- Ungültige/fehlende Felder führen zu klarer Fehlermeldung, nicht zum Absturz.

---

## 5. Verarbeitungsablauf (ein Lauf)

Es gibt einen Lauf-Typ mit eingebauter Vorschau und Bestaetigung (kein separater
dry-run-Modus).

1. Sammeln: Alle Paperless-Dokumente mit Tag `qsl-card` abrufen, OCR-Text holen.
2. Parsen: Aus dem OCR-Text Kandidatenwerte extrahieren (Rufzeichen, Datum, Band, Mode).
3. Vorfilter Log4OM: Nur QSOs als Match-Kandidaten, deren Papier-QSL noch NICHT bestaetigt
   ist. eQSL/LoTW/QRZ etc. werden weder gelesen-als-Grund noch geschrieben.
4. Matchen (siehe §6): pro Karte Ergebnis sicher / unsicher / kein Match.
5. Vorschau anzeigen: Geplante Bestaetigungen (sichere Auto-Treffer) sowie die unsicheren
   und kein-Match-Karten werden angezeigt; Zusammenfassung z. B. '12 wuerden bestaetigt,
   5 unsicher, 3 kein Match'. Pro Karte/QSO werden zudem bereits vorhandene Bestätigungen
   (Typen mit R="Yes", z. B. EQSL, LOTW) angezeigt, sofern vorhanden — als Kontext, damit
   der Nutzer versehentlich getaggte eQSL-/LoTW-Ausdrucke erkennt, bevor er „Jetzt schreiben"
   klickt. Diese Anzeige ändert die Einstufung nicht (→ §6.4). Noch nichts geschrieben.
6. Manuell ergaenzen (optional): Im selben Durchgang kann der Nutzer unsichere Karten ueber
   den manuellen Zuordnungs-Bildschirm zuordnen (§9). Diese manuellen Zuordnungen kommen in
   denselben Korb geplanter Aenderungen wie die automatischen sicheren Treffer.
7. Bestaetigen & Schreiben: Erst auf Klick 'Jetzt schreiben' laeuft EINE gesammelte
   Transaktion fuer ALLE geplanten Aenderungen (auto + manuell) zusammen: Vor-Backup ->
   DB-Transaktion -> Paperless-Tags (§7). 'Abbrechen' verwirft alles ohne Aenderung.
8. Abschluss: Ergebnis/Logeintrag; verbleibende unsichere/kein-Match-Karten bleiben in der
   Liste bzw. kommen beim naechsten Lauf erneut zur Wiedervorlage.

**Akzeptanzkriterien:**
- Vor dem Klick 'Jetzt schreiben' wird garantiert nichts geschrieben (weder DB noch Tags),
  aber die vollstaendige Vorschau ist erzeugt.
- 'Abbrechen' hinterlaesst DB und Tags unveraendert.
- Auto-Treffer und manuelle Zuordnungen werden in EINER Transaktion gemeinsam geschrieben.
- Bereits Papier-QSL-bestaetigte QSOs erscheinen nie als Kandidat.

---

## 6. Matching-Logik

### 6.1 Datenquellen-Priorität pro Karte

Für jede Karte werden Felder in dieser Reihenfolge bezogen — höhere Quelle schlägt niedrigere:

1. **QR-Code** (beste Qualität; nur auf modernen Karten vorhanden)
2. **OCR-Text** (Paperless-OCR; unzuverlässig, braucht Normalisierung)
3. **Manueller Zuordnungs-Bildschirm** (Fallback wenn QR und OCR versagen; § 9)

### 6.2 QR-Code-Auswertung

**Wichtig:** Der QR-Code-Inhalt ist **nicht** im Paperless-OCR-Textfeld (`content`)
enthalten — Tesseract dekodiert QR-Codes nicht (empirisch bestätigt, Schritt 3b,
→ `docs/discovery.md` §5.2). QSL73 muss den QR-Code **client-seitig aus dem
Kartenbild/PDF dekodieren**.

**Ablauf QR-Pfad:**
1. Dokument-Bytes via `GET /api/documents/{id}/download/` holen.
2. **Alle** PDF-Seiten in Rasterbilder rendern (z. B. `pymupdf`) — QSO-Daten können auf
   Vorder- oder Rückseite stehen, beide Seiten werden durchsucht.
3. In jedem gerenderten Bild alle QR-Codes suchen und dekodieren (z. B. `pyzbar`).
4. Jeden dekodierten QR-Inhalt auf **gültiges QSO-Format** prüfen: enthält er die
   erwarteten Schlüssel (`From`, `To`, `Date`, `Band`, `Mode`)? Den ersten gültigen QR
   verwenden; ungültige ignorieren (z. B. Druckdienst-/Werbe-Codes wie Zazzle).
5. Schlägt Decoding fehl, liefert kein QR einen gültigen QSO-Inhalt oder ist kein QR
   vorhanden → Fallback auf §6.3 (OCR).

Moderne Karten (z. B. DARC-QSL-Service) tragen einen QR-Code mit QSO-Daten als
strukturierten Klartext. Bekanntes Format (tolerant gegenüber Feldreihenfolge/Varianten):

```
From: DK8NE  To: DH3KR
Date: 02.04.25  Time: 19:42  Band: 6m  Band_RX: 6m  Mode: FT8  Prop_Mode: TR  RST: -24  QSL: TNX
```

- **From** = Rufzeichen der Gegenstation (Match-Schlüssel gegen Log4OM `callsign`).
- **To** = eigener Call; toleranter Abgleich gegen `log4om.own_callsign` (siehe §6.3
  „Rufzeichen / From-To-Logik") — portabel geänderte Calls (z. B. `SV9/DH3KR`) werden
  korrekt dem eigenen Log zugeordnet.
- **Date/Time** → normalisieren (siehe §6.3).
- **Band/Mode** → normalisieren (siehe §6.3); QR liefert Klartext-Band (`6m`), kein OCR-Artefakt.
- Ein sauberer QR-Treffer (alle vier Pflichtfelder eindeutig) **darf auto-bestätigen**,
  wenn Rufzeichen + Datum + Band + Mode passen — identische Regel wie beim OCR-Match.
  Sicherheitsschleife bleibt die gemeinsame Vorschau + Bestätigung (Schreibmodell B).
- Nicht jede Karte hat einen QR-Code; nicht jeder QR-Code enthält QSO-Daten (z. B.
  Druckdienst-/Werbe-Codes). Mehrere QR-Codes pro Karte möglich — den ersten mit gültigem
  QSO-Format verwenden. QR ist ein Bonus, kein Universalersatz.

### 6.3 OCR-Normalisierung

OCR-Text ist fehleranfällig. Vor dem Matching sind alle Felder zu normalisieren.

**Empirischer Befund (Schritt 3b, → `docs/discovery.md` §5.2):** Das Band-Feld ist das
unzuverlässigste OCR-Feld (z. B. `"6m"` → `"tToemvem"`); handschriftliche Karten sind
via OCR meist nicht matchbar. Im Alltag ist der manuelle Pfad (§6.4 / §9) daher häufig
der einzig gangbare Weg für ältere oder handschriftliche Karten.

**Daten-Position:** QSO-Daten können auf Vorder- oder Rückseite stehen. QSL73 wertet
**alle Seiten** des PDFs aus — für QR-Suche (§6.2, alle Seitenbilder) und für OCR-Text
(Paperless-OCR liefert Volltext aller Seiten im `content`-Feld).

**Datum — unterstützte Formate:**

| Format | Beispiel | Anmerkung |
|--------|----------|-----------|
| `TT.MM.JJ` | `02.04.25` | häufigste europäische Kurzform |
| `TT/MM/JJ` | `3/10/92` | ältere europäische Variante |
| `TT Monatsname JJJJ` | `23Apr2025` | Monatsname 3-buchstabig oder ausgeschrieben |
| `YYYY-MM-DD` | `2024-06-21` | ISO; direkt übernehmbar |
| US-getrennte Spalten | Month=`06` Day=`21` Year=`2024` | aus getrennten Tabellenfeldern zusammensetzen |
| `MM/DD/YYYY` | `06/21/2024` | US-Langform |
| `MM/DD/YY` | `06/21/24` | US-Kurzform |

- Zweistellige Jahreszahl: `>= 30` → 19xx, `< 30` → 20xx (Heuristik, kann falsch sein).
- Mehrdeutige Formate (z. B. `03/04/25` — Tag/Monat oder Monat/Tag?) → **unsicher**.
- Unbekannte/exotische Formate (z. B. römische Monatsziffern `17-XI-93`) werden **nicht**
  per Sonderregel erschlossen — Grundsatz: lieber „Datum nicht normalisierbar" → **unsicher**
  als ein Rategespräch über undokumentierte Formate. Manuelle Zuordnung (§9) fängt das auf.
- Ziel: ISO-Datum `YYYY-MM-DD` für Vergleich mit `qsodate`.

**Band (OCR-unzuverlässigstes Feld):**
- Bandname direkt: `6m`, `2m`, `40m` etc. → direkt übernehmen.
- Frequenz → Band-Umrechnung (Mindesttabelle):

| Frequenzbereich (MHz) | Band |
|-----------------------|------|
| 1.8 – 2.0 | 160m |
| 3.5 – 4.0 | 80m |
| 7.0 – 7.3 | 40m |
| 10.1 – 10.15 | 30m |
| 14.0 – 14.35 | 20m |
| 18.068 – 18.168 | 17m |
| 21.0 – 21.45 | 15m |
| 24.89 – 24.99 | 12m |
| 28.0 – 29.7 | 10m |
| 50.0 – 54.0 | 6m |
| 70.0 – 70.5 | 4m |
| 144.0 – 148.0 | 2m |
| 430.0 – 440.0 | 70cm |
| 1240.0 – 1300.0 | 23cm |

Höhere Mikrowellenbänder (9cm, 6cm, 3cm, …) werden **bewusst nicht** abgedeckt —
unbekanntes Band → `None` → Einstufung **unsicher** → manueller Pfad (§9). Lieber
„nicht erkennbar" als ein fehleranfälliges Mapping auf Exoten-Bänder.

- OCR-Fehler im Bandfeld (z. B. `"tToemvem"` statt `"6m"`) → kein Mapping möglich → Feld
  als fehlend markieren → Karte landet bei **kein Match** oder **unsicher**.

**Mode:**
- Moderne Bezeichnung direkt: `FT8`, `SSB`, `CW`, `AM`, `FM`, `RTTY` etc. → direkt übernehmen.
- Ältere/alternative Bezeichnungen (Mapping-Tabelle, mind.):

| OCR-Wert | Normalisiert |
|----------|-------------|
| `J3E`, `A3J`, `USB`, `LSB`, `PH` | `SSB` |
| `2×SSB`, `2xSSB` | `SSB` (Zweiseitenband-Angabe auf franz. Karten) |
| `A1A` | `CW` |
| `A3E` | `AM` |
| `F3E` | `FM` |
| `F1B`, `RTTY` | `RTTY` |
| `JT65`, `JT9` | jeweiliger Wert |

- Unbekannte Mode-Bezeichnung → Fuzzy-Match gegen bekannte Modi; kein Treffer → **unsicher**.

**Normalisierung beim Vergleich — normalisiert-gegen-normalisiert:**

Beim Matching werden Kartenwert **und** der frisch aus der DB gelesene Kandidatenwert
jeweils im Speicher durch dieselbe Normalisierungsfunktion (`normalize_band` /
`normalize_mode`) geschickt, bevor sie verglichen werden. Damit matchen äquivalente
Schreibweisen korrekt: z. B. Log4OM-DB-Wert `USB` oder `LSB` gegen Karte `SSB`
(alle → `SSB`); oder DB-Wert `A1A` gegen Karte `CW`.

Diese Normalisierung ist eine **rein lesende In-Memory-Operation** auf einer Kopie
des gelesenen Werts — der DB-Rohwert wird NICHT zurückgeschrieben.
Ein nicht normalisierbarer DB-Wert (ergibt `None`) zählt als Widerspruch und schließt
den Kandidaten aus (kein falscher Treffer durch unbekannte DB-Schreibweisen).

Das DB-Datum (`qsodate`-Format: `'YYYY-MM-DD HH:MM:SSZ'`, siehe `docs/discovery.md`)
wird für den Tagesvergleich im Speicher auf `YYYY-MM-DD` reduziert; kein DB-Write.

**Rufzeichen — Stammrufzeichen-Zerlegung:**

Rufzeichen mit `/` werden zerlegt. Reihenfolge (Kurzschluss nach erstem Treffer):

| Fall | Erkennungsregel | Stammrufzeichen |
|------|----------------|-----------------|
| a) | Teil **nach** `/` ist bekanntes Suffix (→ `matching.portable_suffixes` in Config) | Teil **vor** `/` (z. B. `DL1EJD/P` → `DL1EJD`) |
| b) | Teil **vor** `/` ist bekannter ITU-Länderpräfix (Code-interne Datendatei) | Teil **nach** `/` (z. B. `5Z4/UA4WHX` → `UA4WHX`) |
| c) | Beide Seiten mehrdeutig / keiner Regel eindeutig zuordenbar | Karte → **unsicher** (kein erzwungenes Match) |

Unbekannte Suffixe lösen kein Parsing-Fehler aus — sie führen zu Fall c) (vorsichtiges Verhalten).
Die ITU-Länderpräfix-Liste ist zu umfangreich für die Config und wird als pflegbare Datendatei /
Konstante im Code geführt (Details: Schritt 4).

**Suffix-Unterschied-Regel:**

Stimmt das Stammrufzeichen überein, aber der Zusatz unterscheidet sich (z. B. Karte `DL1EJD`,
Log `DL1EJD/P`, oder umgekehrt):
- → **sicher** nur, wenn Datum + Band + Mode **eindeutig** übereinstimmen (genau ein Kandidat).
- → **unsicher**, wenn bei Datum/Band/Mode irgendeine Unschärfe besteht (mehrere Kandidaten,
  Band nicht normalisierbar, Datum mehrdeutig). Nie raten.

**Rufzeichen / From-To-Logik:**
- `From` (QR) bzw. führendes Rufzeichen im OCR = Gegenstation = Match-Schlüssel gegen
  Log4OM `callsign` (nach Stammrufzeichen-Zerlegung). Dieser Wert wird **nie** als eigener
  Call interpretiert.
- `To` (QR) bzw. `"To Radio:"` o. ä. (OCR) = eigener Call — **Zugehörigkeitsprüfung**:
  - Abgleich gegen (a) `log4om.own_callsign` aus der Config **und** (b) alle in der
    Log4OM-DB tatsächlich vorkommenden `stationcallsign`-Werte — jeweils mit
    Stammrufzeichen-Zerlegung (Portabel-Präfixe/-Suffixe werden beidseitig abgetrennt).
  - Stimmt keiner der eigenen Calls (nach Zerlegung) mit dem `To`-Feld überein
    → Karte gehört nicht zu diesem Log → überspringen.
  - `own_callsign` in der Config ist der manuelle Anker/Fallback; der `stationcallsign`-
    Abgleich deckt portabel geloggte eigene Calls ab, die nur in der DB stehen.
  - Hinweis: Der Match-Schlüssel für das QSO-Matching bleibt `From` ↔ `callsign`;
    `To` dient ausschließlich der Zugehörigkeitsprüfung.
- Rufzeichen case-insensitiv; Fuzzy-Toleranz 1 Zeichen (Levenshtein) bei Fuzzy=an (gegen OCR-Verleser).
- Band und Mode werden **normalisiert-gegen-normalisiert** verglichen (kein Fuzzy);
  beide Seiten (Karte und gelesener DB-Wert) laufen im Speicher durch dieselbe Normalisierungsfunktion,
  dann Exakt-Vergleich. Damit matchen z. B. DB-Wert `USB` oder `LSB` korrekt gegen Karte `SSB`.
  Ein nicht normalisierbarer DB-Wert (→ `None`) schließt den Kandidaten aus (kein falscher Treffer).

### 6.4 Match-Ergebnis

**Drei Feldzustände (ADR-0016):**

Für jedes der vier Matchfelder (Rufzeichen, Datum, Band, Mode) gilt gegenüber einem
Kandidaten-QSO einer von drei Zuständen:

| Zustand | Bedingung | Wirkung |
|---------|-----------|---------|
| **STIMMT ÜBEREIN** | Kartenfeld lesbar (≠ None) und passt zum Kandidaten | positiv, trägt zur 3-von-4-Schwelle bei |
| **FEHLT / UNBESTIMMT** | Kartenfeld ist `None` (OCR kaputt oder nicht normalisierbar) | neutral — schließt nicht aus, zählt nicht positiv |
| **WIDERSPRICHT** | Kartenfeld lesbar (≠ None) und stimmt **nicht** mit Kandidaten überein | schließt diesen Kandidaten aus der Treffermenge aus |

**Eingrenzung (Kandidatensuche):**
- Startmenge: alle QSOs, deren Rufzeichen zum Stammrufzeichen der Karte passt
  (exakt oder Fuzzy-1 bei `fuzzy_enabled=True`).
- Für jedes weitere **lesbare** Kartenfeld (Datum, Band, Mode): Kandidaten mit
  Widerspruch werden ausgeschlossen. Fehlende Felder (`None`) grenzen nicht ein.
- Ergebnis: Menge der Kandidaten, die in keinem lesbaren Feld widersprechen.

**Rufzeichen:**
- Fuzzy-Toleranz von 1 Zeichen (Levenshtein) bei `fuzzy_enabled=True`, um OCR-Verleser
  abzufangen. Fuzzy in den Einstellungen abschaltbar.

**Band und Mode:**
- Immer **exakt** verglichen (case-insensitiv), unabhängig von `fuzzy_enabled`.
  Begründung: Band und Mode sind kleine, feste Wertemengen; 1 Zeichen Unterschied bedeutet nach
  Normalisierung einen anderen realen Wert. OCR-Verleser werden bereits durch
  `normalize_band`/`normalize_mode` auf `None` normalisiert; Fuzzy auf Band/Mode würde
  Falsch-Positive erzeugen (ADR-0007).

**Einstufung:**
- **0 Kandidaten** → **kein Match**.
- **Mehrere Kandidaten** → Uhrzeit-Tie-Breaker (±30 min); bleibt mehr als einer → **unsicher**.
- **Genau 1 Kandidat** → **sicher** nur wenn BEIDE Bedingungen erfüllt:
  - (a) mindestens **3 der 4 Felder STIMMEN ÜBEREIN** (positiv gezählt),
  - (b) kein lesbares Kartenfeld widerspricht (durch Eingrenzung bereits sichergestellt).
  - Sind weniger als 3 Felder positiv (z. B. nur Rufzeichen + Datum, Rest fehlt) → **unsicher**.
  - Das Rufzeichen ist immer Pflichtbestandteil der 3; ohne Rufzeichen-Treffer gibt es
    keinen Kandidaten.

- **kein Match** ≠ „nicht bestätigt" (unterschiedliche Zustände, getrennt behandeln).

**Suffix-Unterschied-Regel (§6.3 / strenger als 3-von-4):**
Stimmt das Stammrufzeichen überein, aber der Zusatz unterscheidet sich, müssen Datum +
Band + Mode alle **explizit übereinstimmen** (kein `None` erlaubt) → erst dann „sicher".

**Zeit-Match-Logik:**
- **Primär:** Datum-Match auf **Tag-Ebene** (`YYYY-MM-DD`). Eine genaue Uhrzeit auf der
  Karte wird **nicht** verlangt (viele Karten nennen nur das Datum; Karten- und Logzeiten
  weichen real oft ab).
- **Tie-Breaker:** Gibt es am selben Tag **mehrere** sonst gleichwertige Kandidaten
  (gleiche Station + Band + Mode), wird die Uhrzeit mit großzügiger Toleranz
  (Vorschlag ± 30 Minuten) zur Unterscheidung herangezogen.
  - Genau ein Kandidat innerhalb des Toleranzfensters → **sicher**.
  - Kein Kandidat im Fenster, oder mehrere Kandidaten auch nach Uhrzeit-Filterung → **unsicher**.
- Hinweis: Der genaue Toleranzwert (± 30 min) wird in Schritt 4 empirisch überprüft.

**Vorhandene Bestätigungen als Zusatzinfo:**
Beim Matchen eines QSOs werden alle Bestätigungstypen mit R="Yes" aus dem `qsoconfirmations`-
Feld ausgelesen (EQSL, LOTW, QRZCOM usw.), ausgenommen das Papier-QSL-Feld selbst. Diese
Information wird als Zusatzfeld an das Match-Ergebnis angehängt und in der Vorschau (§5, §9)
pro Karte angezeigt (z. B. „bereits bestätigt via: EQSL, LOTW"), sofern Bestätigungen vorliegen.

Die Einstufung sicher/unsicher/kein Match wird dadurch **nicht** verändert — kein Blockieren,
keine automatische Herabstufung. Begründung: Ein vorhandener eQSL-Eintrag ist kein
zuverlässiger Indikator dafür, dass die eingescannte Karte eine eQSL ist — Doppelbestätigungen
(eQSL + Papierkarte für dasselbe QSO) sind unter Funkamateuren häufig und legitim.
Die Anzeige soll dem Nutzer helfen, versehentlich mit `qsl-card` getaggte eQSL-/LoTW-Ausdrucke
selbst zu erkennen, bevor er „Jetzt schreiben" klickt (Transparenz statt Filterlogik; ADR-0015).

**OCR-Quelle:** QSL73 nutzt die **Paperless-OCR** (`GET /api/documents/{id}/?fields=content`),
nicht eine evtl. in der PDF eingebettete OCR. Qualität variiert; Befund siehe
`docs/discovery.md` §5.2 (Schritt 3b).

**Akzeptanzkriterien:**
- Ein QSO mit exakt passenden vier Feldern wird als „sicher" erkannt (4/4).
- Genau 3 von 4 Feldern positiv (ein Feld fehlt/None), kein Widerspruch, 1 Kandidat → „sicher" (3-von-4-Regel, ADR-0016).
- Nur 2 oder weniger Felder positiv (zwei oder mehr fehlen) → „unsicher".
- Lesbares Kartenfeld widerspricht dem Kandidaten → Kandidat ausgeschlossen; bleibt kein Kandidat → „kein Match". Kein Kandidat ohne aktiven Widerspruch wird durch ein einzelnes fehlendes Feld ausgeschlossen.
- Karte mit lesbarem Band 20m, DB hat QSOs auf 6m und 20m am selben Tag: das 6m-QSO wird ausgeschlossen; das 20m-QSO ist der einzige verbleibende Kandidat → „sicher".
- Karte ohne lesbares Band, DB hat QSOs auf 6m und 20m: beide bleiben (kein Widerspruch) → „unsicher" (zwei Kandidaten).
- Ein um 1 Zeichen abweichendes **Rufzeichen** (bei mind. 2 weiteren übereinstimmenden Feldern) matcht bei Fuzzy=an als „sicher", bei Fuzzy=aus als „kein Match".
- Verschiedene Bänder oder Modi — auch wenn sie sich nur um 1 Zeichen unterscheiden (z. B. `"6m"` vs. `"2m"`, `"FT8"` vs. `"FT4"`) — ergeben **niemals** „sicher"; sie werden exakt verglichen und schließen den Kandidaten aus.
- Zwei gleich gut passende Kandidaten ergeben „unsicher", nie eine Auto-Bestätigung.
- Karte mit gültigem QR-Code (QSO-Felder vorhanden) → Felder aus QR, bevorzugt.
- QR-Code ohne gültiges QSO-Format (z. B. Werbe-/Druckdienst-Code) → ignoriert,
  Fallback auf OCR; kein Absturz, kein Falsch-Match.
- Karte ohne QR → Fallback auf OCR-Normalisierung.
- QSO-Daten auf der Vorderseite eines PDFs werden ebenso gefunden wie auf der Rückseite.
- `"6m"` und `"50.100 MHz"` ergeben dasselbe Band; `"144.255 MHz"` → `"2m"`.
- `"J3E"`, `"USB"`, `"LSB"`, `"2×SSB"`, `"2xSSB"` → `"SSB"`.
- `"23Apr2025"` wird korrekt zu `2025-04-23` normalisiert.
- US-Spaltenformat Month=`06` Day=`21` Year=`2024` → `2024-06-21`.
- Unbekanntes Datumsformat (z. B. römische Monatsziffern `17-XI-93`) → **unsicher**,
  kein Absturz, kein Rate-Match; manuelle Zuordnung greift.
- `To: SV9/DH3KR` bei `own_callsign = DH3KR` → Karte korrekt als eigenes Log erkannt.
- Karte adressiert eigenen portablen Call (`[EIGENCALL]/P`), der nur in `stationcallsign`
  der DB steht (nicht in `own_callsign`) → Karte wird korrekt als eigenes Log erkannt.
- `From`/`To` korrekt unterschieden; Stammrufzeichen von `To` stimmt nicht überein → Karte übersprungen.
- `DL1EJD/P` im Log, `DL1EJD` auf Karte (oder umgekehrt): bei sonst exakten Feldern → **sicher**;
  bei jeder Unschärfe bei Datum/Band/Mode → **unsicher**.
- `5Z4/UA4WHX` auf Karte → Stammrufzeichen `UA4WHX` (Präfix erkannt) → korrekt gegen Log abgeglichen.
- `[CALL]/IF9` (Fall c, mehrdeutig) → **unsicher**, kein erzwungenes Match, kein Absturz.
- Zwei QSOs derselben Station am selben Tag, Karte nennt nur das Datum → Uhrzeit-Tie-Breaker;
  bleibt mehrdeutig → **unsicher**.

---

## 7. Schreibstrategie (Datensicherheit)

> Schutz vor STRUKTUR-Änderungen durch Log4OM-Updates: → §3.3 (Schema-Validierung).
> Dieser Abschnitt behandelt ausschließlich den Schutz vor DATEN-Änderungen zur Laufzeit.

- **WAL-Modus** für technische Absturzsicherheit (selbstheilend bei Abbruch).
- **Erst sammeln (inkl. Vorschau+Bestaetigung), dann gesammelt schreiben:** alle Aenderungen
  - automatische sichere Treffer UND manuelle Zuordnungen - nach Klick 'Jetzt schreiben' in
  **einer SQLite-Transaktion** (alles-oder-nichts, kein halb geschriebener Zustand).
- **Reihenfolge:** (1) DB-Transaktion erfolgreich, DANN (2) Paperless-Tags setzen.
  - DB scheitert → keine Tags (kein Widerspruch).
  - Nur Tag-Setzen scheitert → QSO korrekt bestätigt; fehlendes Tag wird beim nächsten
    Lauf nachgezogen.
- **Vor-Backup nur beim tatsaechlichen Schreiben** (Klick 'Jetzt schreiben'); reines
  Ansehen/Abbrechen oder 'nichts zu schreiben' -> kein Backup. Schuetzt vor inhaltlichen
  Fehlern (falsche Zuordnung), wogegen WAL nicht hilft.
- **Backup-Aufbewahrung:** konfigurierbar, **Default 5**, ältere automatisch löschen.
  Einstellungen zeigen Hinweis + Live-Speicheranzeige der Backups + „Backup-Ordner öffnen".

### Nebenläufigkeit & DB-Änderungsschutz

Log4OM ist der **Eigentümer** der SQLite-DB; QSL73 schreibt als **Gast**, defensiv und
ohne Annahme exklusiven Zugriffs. Log4OM kann parallel laufen und die DB verändern.

- **SQLITE_BUSY abfangen:** Scheitert eine Schreiboperation wegen eines gesperrten Locks
  (`SQLITE_BUSY`), kurz warten und begrenzt wiederholen (z. B. 3 Versuche, ~300 ms Pause).
  Bleibt die DB gesperrt, sauberer Abbruch mit klarer Meldung an den Nutzer — kein Crash,
  kein unvollständig geschriebener Zustand.
- **Änderungserkennung (time-of-check/time-of-use):** Beim Sammeln einen DB-Zustand-
  Fingerabdruck speichern: bevorzugt `PRAGMA data_version` (SQLite-eigener Änderungszähler),
  als Fallback `mtime + Dateigröße`. Direkt **vor dem Schreiben** (nach Klick „Jetzt
  schreiben") erneut prüfen — hat sich der Fingerabdruck verändert, gilt die gesammelte
  Vorschau als veraltet.
- **Pro-QSO-Gegenprüfung (optimistic locking):** Innerhalb der Schreib-Transaktion für
  jedes QSO kurz verifizieren, dass es noch im erwarteten Zustand ist: Papier-QSL-Feld
  noch offen, Call/Datum/Band/Mode unverändert. Nur dann schreiben.
- **Reaktionsmodell (kombiniert):**
  - Einzelne zwischenzeitlich veränderte QSOs werden **übersprungen** und im `audit.log`
    vermerkt (Rufzeichen, Änderungsgrund); der Rest der Transaktion läuft normal durch.
  - Hat sich der **DB-Gesamtzustand** grundlegend geändert (Fingerabdruck-Abweichung),
    wird der gesamte Schreibvorgang **abgebrochen** und dem Nutzer angeboten, neu einzulesen.
- **Log4OM-Running-Erkennung:** Vor dem Schreiben aktiv prüfen, ob der Log4OM-Prozess
  läuft. Wenn ja: **nicht blockierende Warnung** zeigen — „Log4OM scheint zu laufen.
  Zum sichersten Schreiben Log4OM kurz schließen. Trotzdem fortfahren?" — Nutzer entscheidet,
  kein Zwangs-Stopp.
- **Log4OM-Neustart nach dem Schreiben (empirisch bestätigt, 2026-06-18):** Log4OM erkennt
  externe Änderungen an einer geöffneten DB nicht automatisch. Ein „Neu laden" innerhalb von
  Log4OM reicht nicht — Log4OM muss **neugestartet** werden, damit die von QSL73 geschriebenen
  Bestätigungen in der Bearbeitungsmaske sichtbar werden. QSL73 soll den Nutzer nach einem
  erfolgreichen Schreibvorgang mit einem klaren Hinweis darauf aufmerksam machen.
  Risiko bei gleichzeitigem Betrieb: nimmt Log4OM selbst Änderungen vor, während QSL73
  gerade schreibt oder geschrieben hat, besteht das Risiko, dass Log4OM die QSL73-Daten
  beim nächsten Speichern überschreibt. Empfehlung: Log4OM während des Schreibvorgangs
  geschlossen halten (verstärkt die bestehende Log4OM-Running-Warnung).
- **Verknüpfung Cloud-/Netzwerk-Warnung:** WAL-Modus erfordert lokales Dateisystem;
  liegt die DB in einem Cloud-Sync-Ordner (OneDrive/Dropbox), gelten beide Warnungen
  (Cloud-Warnung aus §3.1 und Nebenläufigkeits-Warnung) kumulativ.

**Akzeptanzkriterien:**
- Simulierter Abbruch mitten im Schreiben → DB bleibt im Zustand vor dem Lauf (Transaktion).
- Nach erfolgreichem commit existiert genau ein neues Vor-Backup; Anzahl respektiert das Limit.
- Tags werden nie gesetzt, wenn die DB-Transaktion fehlgeschlagen ist.
- Simulierte DB-Änderung zwischen Sammeln und Schreiben → betroffene QSOs werden übersprungen
  und im audit.log vermerkt; bei umfangreicher Gesamtänderung bricht der Lauf sauber ab.
- `SQLITE_BUSY` führt zu Retry + klarer Meldung, nie zum Absturz.
- Bei laufendem Log4OM-Prozess erscheint die nicht-blockierende Warnung vor dem Schreiben.

---

## 8. Paperless-Tags (Setup-Defaults, anpassbar)

- `qsl-card` → zu verarbeitende Karten (nur diese werden gelesen).
- `qsl-bestätigt` → gesetzt bei sicherem Match ODER nach manueller Zuordnung.
- `qsl-nicht-bestätigt` → gesetzt nur bei unsicherem/mehrdeutigem Treffer.
- kein Status-Tag → bei „kein Match" (Wiedervorlage).
- Tag-Namen im Setup frei wählbar (für bestehende Paperless-Installationen).

**Nutzungs-Voraussetzung — Tagging-Disziplin:**
QSL73 verarbeitet alle Dokumente mit dem `qsl-card`-Tag und behandelt sie ausnahmslos als
**echte Papierkarten**. Nur physische QSL-Karten sollten diesen Tag erhalten.
eQSL-/LoTW-Ausdrucke sind keine Papierkarten und gehören nicht in diese Kategorie.
QSL73 kann ausgedruckte eQSLs nicht per Bildanalyse von echten Papierkarten unterscheiden —
das wäre unzuverlässig (ADR-0015). Stattdessen zeigt QSL73 vorhandene Bestätigungen in der
Vorschau an, damit der Nutzer Fehltaggings selbst erkennen und korrigieren kann.

Wenn Paperless automatische Tag-Vergabe (KI) nutzt, sollte der Nutzer sicherstellen, dass
`qsl-card` nicht unbeabsichtigt an eQSL-/LoTW-Ausdrucke vergeben wird. Die Verantwortung
für korrekte Verschlagwortung liegt beim Nutzer.

---

## 9. GUI (tkinter)

- **Sprache:** DE Default, EN umschaltbar (Einstellungen).
- **Optik:** schlicht/sachlich, heller Standard-Look; Programm-Icon (Titelleiste/Startmenü/EXE).
- **Single-Instance:** nur eine laufende Instanz (Lock), kein paralleles DB-Schreiben.
- **Hauptbereich:** Lauf starten; laufende Konsolen-/Log-Ausgabe inkl. Netzwerkaktionen
  live; nach dem Matchen Vorschau der geplanten Aenderungen + Buttons 'Jetzt schreiben' /
  'Abbrechen'.
- **Ergebnis-Liste:** lightweight Filter „unsicher" / „kein Match" / „beides". Pro Eintrag
  werden — sofern vorhanden — bereits bestätigte Typen angezeigt (z. B. „bereits: EQSL,
  LOTW"), als Kontext für die Nutzer-Entscheidung. Keine Sperrlogik; reine Information
  (→ §6.4, ADR-0015). Muss mit sehr vielen Einträgen flüssig bleiben.
- **Manueller Zuordnungs-Bildschirm (Kern-Feature):**
  - Karten-Bild (Vorder-/Rückseite), **erst beim Anklicken** der Karte nachladen.
  - Eingabefelder daneben, mit OCR-Vorschlag vorbefüllt (z. B. Rufzeichen).
  - **Live-Suche während des Tippens** gegen die Log4OM-DB: passende QSOs (Datum/Band/Mode)
    sofort als Vorschläge; Nutzer wählt das richtige QSO und ordnet zu.
  - Manuelle Zuordnung = wie Auto-Match: QSO markieren + Tag `qsl-bestätigt`.
- **Fehler-Prompt:** verständliche Kurzmeldung mit **aufklappbarem Detailbereich** (Stacktrace).
- **Setup-Assistent** beim ersten Start; alle Werte später in **Einstellungen** änderbar.
- **Einstellungen — QSL-Route-Default (RV):** Standardwert für das Feld „Received Via"
  bei Papier-QSL-Bestätigungen. Optionen: **Undefined** (Default), **Bureau**, **Direct**.
  „Electronic" wird nicht angeboten (fachlich falsch für Papier-QSL; Electronic = LOTW/eQSL).
  Wert gilt pauschal für alle von QSL73 gesetzten Bestätigungen (kein Pro-Karte-Override).
- **Hilfe → „Über / Datenschutz"-Dialog:** listet die 3 Verbindungen, stellt klar dass keine
  Daten an den Entwickler gehen, nennt lokale Speicherorte, verlinkt das Repo; Buttons
  „Log-Ordner öffnen", „Backup-Ordner öffnen"; Kontakt: GitHub-Issues + QRZ-Link
  (https://www.qrz.com/db/DF1DS).

**Akzeptanzkriterien:**
- Zweite Programminstanz startet nicht (oder fokussiert die bestehende).
- Liste mit z. B. 2000 Einträgen scrollt/filtert ohne spürbare Verzögerung; Bilder erst on click.
- Live-Suche zeigt bei Eingabe eines gültigen Rufzeichens die passenden QSOs.

---

## 10. Logging & Fehler-Reporting

- Zwei Logs in `%APPDATA%\QSL73\logs\`:
  - `audit.log` → fachliche Änderungen (Zeitstempel, Dok-ID, QSO Rufzeichen/Datum/Band/Mode,
    auto vs. manuell, Backup ja/nein).
  - `qsl73.log` → technisches Diagnose-Log mit Leveln (INFO/WARNING/ERROR).
- **Log-Rotation:** Maximalgröße pro Datei, Archiv-Rotation, nur wenige behalten.
- **Fehler-Reporting on demand** (kein Auto-Versand, kein Account-Zwang):
  - „Auf GitHub melden" → vorausgefülltes Issue im Browser (Account nötig).
  - „Bericht lokal speichern/teilen" → Datei ablegen; Nutzer entscheidet über Weitergabe.
  - Bericht **bereinigt**: nur QSL73-Version, Windows-Version, Fehlertyp/Stacktrace,
    Aktionskontext. KEINE Tokens/Passwörter/URL/QSO-Inhalte. Nutzer sieht ihn vor Versand.
- **Kein eingebettetes Token** in der App.

**Akzeptanzkriterien:**
- Ein provozierter Fehler erzeugt einen Logeintrag in `qsl73.log` und einen aufklappbaren Prompt.
- Der generierte Bericht enthält nachweislich keine Secrets/QSO-Inhalte.

---

## 11. „Telefoniert nicht nach Hause"

- Keine Telemetrie, keine Daten an Entwickler/zentralen Server.
- Genau 3 mögliche Verbindungen: (1) eigenes Paperless, (2) lokale Log4OM-Datei (kein Netz),
  (3) GitHub – ausschließlich für Update-Prüfung/Download.
- Automatische Update-Prüfung in den Einstellungen abschaltbar.

---

## 12. Update-Lifecycle

- **Prüfung:** beim Start (abschaltbar) + Button „Auf Updates prüfen", gegen die
  **GitHub-Releases-API** (Tag `vX.Y.Z` + Release Notes).
- **Flow:** Hinweis mit neuen Features → „Jetzt"/„Später". Bei „Jetzt": Installer laden →
  eigener **Updater** startet, QSL73 schließt sich → Updater zeigt Fortschritt, führt den
  **Inno-Installer still** aus (ersetzt nur Geändertes, räumt Altes weg) → Erfolg → „OK"
  startet die neue Version.
- **Config-Migration** beim ersten Start nach Update (siehe §4).

**Akzeptanzkriterien:**
- Bei vorhandener neuerer Release-Version erscheint der Hinweis inkl. Release-Notes.
- Nach Update läuft die neue Version, alte/überflüssige Dateien sind entfernt, Config migriert.

---

## 13. Installer / Deinstaller (Inno Setup)

- Installation pro Maschine nach `C:\Program Files\QSL73`; sauber in Registry,
  Windows-Deinstallationsliste, Startmenü. Programm-Icon eingebunden.
- **Kein Autostart** – nur manueller Start.
- **Deinstaller** entfernt Programmdateien, Registry-Einträge, Verknüpfungen restlos und
  **fragt**, ob Nutzerdaten (`%APPDATA%\QSL73`) ebenfalls gelöscht werden sollen.

**Akzeptanzkriterien:**
- Nach Deinstallation (ohne Nutzerdaten-Löschung) sind nur noch `%APPDATA%\QSL73` Daten übrig.
- Mit Nutzerdaten-Löschung bleibt nichts zurück.

---

## 14. Versionierung & Doku (von Claude Code geführt)

- **SemVer MAJOR.MINOR.PATCH.** PATCH=Bugfix, MINOR=neue Funktion (abwärtskompatibel),
  MAJOR=Bruch (z. B. Config ohne Migration). Immer nur eine Stelle erhöhen, niedrigere auf 0.
- Veröffentlichte Releases nie nachträglich ändern → nur neue Version.
- Start `0.x.y`; erste stabile/benutzbare Version = `1.0.0`.
- **CHANGELOG.md** im Repo pflegen. Eingebaute Version = Git-Tag = GitHub-Release; Changelog,
  Release-Notes und Tag konsistent.

---

## 15. Repo, Lizenz, Branding

- GitHub öffentlich, Account **kainomatic**, Repo z. B. `qsl73`. Branches: `main` (stabil),
  `dev` (laufend), `feature/*` (von `dev`).
- Keine Secrets im Repo: `.gitignore` + `config.example.yaml`.
- **Lizenz GPLv3** (`LICENSE`-Datei). Inhaber-Infos (DF1DS, kainomatic, QRZ-Link) im
  „Über"-Dialog, EXE-Metadaten, `LICENSE`, `README`.
- **Logo/Icon:** Originaldatei `qsl73logo.png` in `assets/` (im Repo). Freistellen +
  `.ico`-Erzeugung (alle Größen; 16/24/32px ggf. vereinfachtes Motiv aus Pfeilen+Haken,
  ab 48px volles Logo) durch Claude Code mit geeignetem Tool – nicht per Skript-Threshold
  (erzeugt Halos). Farben: Blau ~#3A78A6, Grün ~#4FA75E.

---

## 16. Release-Kanäle (Stable und Beta)

QSL73 bietet zwei parallel installierbare Varianten, damit neue Features gefahrlos
vorab getestet werden können, ohne die produktive Stable-Installation zu gefährden.

### 16.1 Zwei getrennte Installationen

| | **Stable** | **Beta** |
|---|---|---|
| Quelle | `main`-Branch | `dev`-Branch |
| Installationspfad | `C:\Program Files\QSL73` | `C:\Program Files\QSL73 Beta` |
| Nutzerdaten | `%APPDATA%\QSL73\` | `%APPDATA%\QSL73-Beta\` |
| Installer | `QSL73-Setup.exe` | `QSL73-Beta-Setup.exe` |

Beide Varianten können auf demselben Rechner gleichzeitig installiert sein, ohne sich
gegenseitig zu stören: getrennte Config, getrennte Backups, getrennte Logs. Jede
Variante hat einen eigenen, separaten Installer — kein gemeinsamer Installer.

### 16.2 Update-Kanäle (bewusst ruhig)

- **Stable** prüft und aktualisiert gegen offizielle GitHub-Releases (aus `main`).
- **Beta** prüft und aktualisiert **ausschließlich gegen explizit getaggte GitHub-Pre-Releases**
  (aus `dev`). Ein `dev`-Stand wird erst dann zum Beta-Update, wenn er bewusst als
  Pre-Release veröffentlicht wird — nicht bei jedem Commit/Push.

### 16.3 BETA-Kennzeichnung

Die Beta-Variante trägt einen deutlich sichtbaren **„BETA"-Hinweis** in der Oberfläche
— mindestens im Fenstertitel und im „Über"-Dialog (→ §9 GUI) — damit jederzeit klar
ist, in welcher Variante der Nutzer arbeitet.

### 16.4 Gemeinsamer Log4OM-DB-Pfad — Hinweis, keine Blockade

Es ist technisch möglich, dass der Nutzer in Stable und Beta denselben Log4OM-DB-Pfad
einträgt; dann greift auch die (experimentelle) Beta auf die produktive DB zu. Das wird
**nicht hard verhindert** (die DB liegt außerhalb von QSL73 und ist Nutzerentscheidung),
aber QSL73 weist klar darauf **hin**:

- beim Einrichten der Beta im Setup-Assistenten (→ §9), und/oder
- wenn die Beta erkennt, dass ihr DB-Pfad mit dem in einer vorhandenen Stable-Konfiguration
  identisch ist.

**Empfehlung:** Beta zunächst gegen eine Kopie der produktiven DB testen.

Das bestehende Sicherheitsnetz bleibt ohnehin wirksam und federt das Risiko ab:
Vor-Backup vor jedem Schreibvorgang + Vorschau/Bestätigung (Schreibmodell B, → §7).

**Umsetzung:** Schritt 8 (kanalabhängige Update-Prüfung) und Schritt 9 (zwei Installer,
BETA-Kennzeichnung, DB-Pfad-Hinweis im Setup-Assistent). → ADR-0021

---

## 17. Tech-Stack

Python 3.11+ (64-Bit), `requests` (Paperless), `sqlite3` (Log4OM, WAL), `rapidfuzz` (Fuzzy),
`PyYAML` (Config), `tkinter` (GUI), `pywin32` (DPAPI), Bild-/PDF-Anzeige (`Pillow` + PDF-Render).

**QR-Code-Pfad (§6.2):** `zxingcpp` (QR-Decoding, rein Python/C++, keine externe DLL) +
`pymupdf` (PDF→Bild-Rendering) + `Pillow` (Bild-Konvertierung für zxingcpp). Das ursprüngliche
`pyzbar`-Risiko (native `libzbar-64.dll` als PyInstaller-Bundle-Abhängigkeit, → ADR-0017) entfällt
durch `zxingcpp` vollständig — Issue #7 ist damit als durch zxingcpp entschärft zu vermerken.

Build: **PyInstaller** → **Inno Setup**. Hinweis: unsignierte EXE löst SmartScreen-Warnung aus.

---

## 18. Bewusst verschoben (V2)

- **Undo** einer Bestätigung (QSO wiederfinden, Status zurücksetzen, Paperless-Tag entfernen).
  Fuer Start nicht noetig (Vorschau+Bestaetigung + Vor-Backup sichern ab).
