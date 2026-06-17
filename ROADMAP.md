# QSL73 – Schrittplan & Review (ROADMAP.md)

> Steuert das **Vorgehen** (Reihenfolge, Discovery, Review-Punkte) – nicht die
> Spezifikation (→ KONZEPT.md). Lebendes Dokument: erledigte Schritte abhaken,
> Reihenfolge bei Bedarf anpassen.

## Zusammenarbeit (Rollen)
- **Claude Desktop:** Architekt + Reviewer. Schreibt/aktualisiert KONZEPT.md & Prompts,
  liest nach jedem Schritt den Repo-Stand (Filesystem, nur lesend) und prüft gegen die
  Akzeptanzkriterien im KONZEPT.md. Schreibt nie selbst ins Repo.
- **User (DF1DS):** Vermittler – überbringt Prompts und Repo-Stände.
- **Claude Code:** baut, committet, testet, versioniert, macht GitHub/Releases/Doku.

**Schleife je Schritt:** Desktop formuliert Auftrag (Kontext+Aufgabe+Akzeptanzkriterien)
→ User überbringt → Claude Code baut & committet → Desktop liest Repo & reviewt →
Korrektur-Auftrag oder Freigabe → nächster Schritt.

**Tests ab Schritt 2:** Jeder Bau-Schritt (2–9) liefert Unit-Tests mit. Ein Schritt gilt
erst als fertig, wenn pytest grün ist und CI (GitHub Actions) durchläuft. → ADR-0009

**Voraussetzung Review-Lesezugriff:** Repo liegt unter `C:\Entwicklung\` (freigegeben),
z. B. `C:\Entwicklung\qsl73`.

---

## ✅ Schritt 0 — Discovery (vor dem ersten Code) — ABGESCHLOSSEN

Ziel: Unbekannte an echten Daten klären, damit später nichts blind gebaut wird.
- **Log4OM-DB (read-only auf Kopie):** Tabellen/Spalten gedumpt; Felder für Rufzeichen,
  Datum/Zeit (UTC), Band, Mode identifiziert; exakt ermittelt, welche Spalte/welcher
  Wert „Papier-QSL bestätigt" bedeutet (Abgrenzung zu eQSL/LoTW/QRZ); Schreibformat
  empirisch bestimmt (zuerst Schätzung, dann per RV-Hand-Test 2026-06-17 bewiesen).
- **Paperless (echte Karten):** 7 echte QSL-Karten analysiert (OCR-Qualität, QR-Pfad,
  API-Endpunkte). Befunde in `docs/discovery.md`.
- **Ergebnis:** `docs/discovery.md` mit allen Befunden inkl. empirisch bestätigtem
  Schreibformat (Issue #1 geschlossen).
- **Review:** Abgenommen; Discovery vollständig.

## ✅ Schritt 1 — Repo-Grundgerüst — ABGESCHLOSSEN

- Struktur, `.gitignore`, `config.example.yaml`, `README.md`, `CHANGELOG.md`, `LICENSE`
  (MIT), Versions-Datei `0.1.0`, `assets/` mit `qsl73logo.png`. Branches `main`/`dev`.
- **Review:** Vollständigkeit/Struktur bestätigt, keine Secrets, Version 0.1.0 gesetzt.

## ✅ Schritt 2 — Config & Setup-Grundlagen — ABGESCHLOSSEN

- Config-Load/Save (`%APPDATA%\QSL73\config.yaml`), DPAPI-Token, Schema-Versionsfeld +
  Migrationsgerüst. Setup-Assistent (Minimalfassung).
  pytest-Gerüst + GitHub-Actions-CI (`/.github/workflows/ci.yml`) eingerichtet.
- **Review:** Token nur verschlüsselt; fehlende Config → Assistent; Migrationsstub
  vorhanden; pytest grün; CI-Workflow grün.

## ✅ Schritt 3 — Paperless-Client — ABGESCHLOSSEN

- Auth (Token & User/PW→Token), Dokumente nach Tag holen, OCR-Text, Bild/Preview, Tag
  PATCH. 56 Unit-Tests gegen Mocks.
- **Review:** Karten lesbar, Bildabruf funktioniert, Fehler bei nicht erreichbarem Server
  sauber abgefangen; pytest grün, CI grün.

## ✅ Schritt 4 — Log4OM-Zugriff (read) + Matching — ABGESCHLOSSEN

Aufgeteilt in zwei Teilschritte:

### ✅ Schritt 4a — Matching-/Normalisierungslogik (freigegeben)

- `normalize.py`: Datum (alle §6.3-Formate), Band (15 Bänder: 160m–23cm inkl. 60m/4m;
  Frequenz-zu-Band-Umrechnung mit Zwei-Pass-Ansatz), Mode (Mapping-Tabelle + Fuzzy).
- `callsign.py`: Rufzeichen-Zerlegung, Eigenrufzeichen-Prüfung gegen own_callsign + alle
  stationcallsign-Werte der DB.
- `matching.py`: **3-von-4 + Widerspruchs-Ausschluss** (ADR-0016): Rufzeichen + mind. 2
  weitere Felder positiv; widersprechende lesbare Felder schließen Kandidaten aus; fehlende
  Felder (None) neutral. **Fuzzy (Levenshtein-1) wirkt ausschließlich auf das Rufzeichen;
  Band und Mode werden exakt normalisiert-gegen-normalisiert verglichen (In-Memory, ADR-0007).**
  Suffix-Unterschied-Regel strenger (ADR-0013). Zeit-Tie-Breaker ±30 min.
- ITU-Präfix-Datendatei (~130+ Einträge), MatchingConfig um portable_suffixes ergänzt.
- ADR-0013/0014/0015/0016 dokumentiert.
- 410+ Tests grün (OCR-Fehlerkatalog, Falsch-Positiv-Fokus, §6.4-Akzeptanzkriterien).

### ✅ Schritt 4b — QR-Decoding + DB-Abnahme (freigegeben)

- `qr.py`: client-seitige QR-Dekodierung aus PDF-Bytes (pymupdf + zxingcpp, ADR-0011/0017).
  Toleranter Key-Value-Parser; ignoriert Werbe-QR; kein Absturz bei Eingabefehlern.
- ADR-0017: zxingcpp statt pyzbar (DLL-Problem auf Windows, Issue #7).
- Abnahme-Tests A–E gegen echte DB-Kopie in tmp_path (Original unverändert, CI-kompatibel).
  A: Anker → CERTAIN · B: gelöscht → NO_MATCH · C: Band-Widerspruch → NO_MATCH ·
  D: Ambiguität → UNCERTAIN · E: gedruckte Karten → CERTAIN.
- 459 Tests gesamt grün; 3 erwartete Skips (DPAPI-Plattform).

**Review (Schritt 4 gesamt):** §6-Akzeptanzkriterien erfüllt; QR-Pfad + OCR-Normalisierung
getestet; QR→OCR→manuell-Priorität korrekt; 3-von-4-Matching mit Widerspruchs-Ausschluss
widerlegt Falsch-Positive zuverlässig; Anker-Negativtest (B) und Band-Widerspruch (C)
bestätigen Falsch-Positiv-Schutz. Freigegeben.

---

## ➡️ Schritt 5 — Schreiblogik (commit) + Backup — NÄCHSTER SCHRITT

**Spezifikationsseitig entsperrt:** Schreibformat empirisch bestätigt (RV-Hand-Test
2026-06-17, `docs/discovery.md §3`, Issue #1 geschlossen).

- Sammeln→Vorschau→Bestätigung(„Jetzt schreiben")→eine Transaktion→Tags; Vor-Backup nur
  beim tatsächlichen Schreiben, Aufbewahrung Default 5. Reihenfolge DB-dann-Tags strikt.
  Auto-Treffer + manuelle Zuordnungen gemeinsam in EINER Transaktion.
- Schreibformat (empirisch bestätigt): `R="Yes"`; `RV`: `"Bureau"`/`"Direct"` (Großbuchstabe)
  oder RV-Feld entfernen (undefined); kein `RD`; `S`/`SV`/`CT` unverändert.
- **Review:** Akzeptanzkriterien §5/§7 (Abbruch-Test, Backup-Anzahl, Tag-nur-nach-DB).
  Nebenläufigkeit: SQLITE_BUSY-Handling, Änderungserkennung (data_version/Fallback),
  Pro-QSO-Gegenprüfung, Log4OM-Running-Warnung getestet.
  Schema-Validierung (§3.3): Check beim Start und vor dem Schreiben; Schreibsperre bei
  umbenannter/fehlender Tabelle oder nicht-parsebarem JSON; robustes Lesen ohne Crash;
  pytest grün, CI grün.

## Schritt 6 — GUI

- Hauptfenster + Log-Ausgabe, Ergebnis-Liste mit Filter, **manueller Zuordnungs-Bildschirm**
  (Kartenanzeige on click, Live-Suche), Fehler-Prompt (aufklappbar), Einstellungen,
  Über/Datenschutz-Dialog, Single-Instance, Icon einbinden.
- **Review:** Akzeptanzkriterien §9; flüssige Liste bei vielen Einträgen; pytest grün, CI grün.

## Schritt 7 — Logging & Fehler-Reporting

- audit.log/qsl73.log + Rotation; On-demand-Bericht (GitHub-Issue / lokal), bereinigt.
- **Review:** Akzeptanzkriterien §10 (Bericht ohne Secrets); pytest grün, CI grün.

## Schritt 8 — Update-Lifecycle + Installer/Deinstaller

- GitHub-Releases-Check, Updater, Inno-Installer (still, aufräumend), Deinstaller mit
  Nutzerdaten-Abfrage, Config-Migration scharf schalten.
- **Review:** Akzeptanzkriterien §12/§13; pytest grün, CI grün.

## Schritt 9 — Build, Test, erstes Release

- PyInstaller-Build (64-Bit), Inno-Setup-Paket, Test auf Win10/11. Versionspflege +
  CHANGELOG, Tag `v0.x.0`, GitHub-Release. Logo/Icon final (Freistellen + .ico durch
  Claude Code).
- **Review:** Lauf Ende-zu-Ende (Vorschau → „Jetzt schreiben") auf echtem System;
  Release konsistent.

---

## Offene Punkte (laufend)

- Reale OCR-Qualität bei „gemischt" (gedruckt + handschriftlich) bestimmt den Anteil
  des manuellen Pfads im Alltag — empirisch bestätigt: handschriftliche und ältere Karten
  dominieren oft; manueller Pfad wird häufig genutzt.
- Bild-Auflösung für lesbare Handschrift (Preview vs. Original) — noch offen.
- pyzbar/libzbar-64.dll auf Windows: Issue #7 (PyInstaller-Bundle). Für Schritt 9 relevant.
