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

**Voraussetzung Review-Lesezugriff:** Repo liegt unter `C:\Entwicklung\` (freigegeben),
z. B. `C:\Entwicklung\qsl73`.

---

## Schritt 0 — Discovery (vor dem ersten Code)
Ziel: Unbekannte an echten Daten klären, damit später nichts blind gebaut wird.
- **Log4OM-DB (read-only auf Kopie):** Tabellen/Spalten dumpen; Felder für Rufzeichen,
  Datum/Zeit (UTC), Band, Mode identifizieren; **exakt** ermitteln, welche Spalte/welcher
  Wert „Papier-QSL bestätigt" bedeutet (Abgrenzung zu eQSL/LoTW/QRZ); Schreibformat für
  „manuell bestätigt" bestimmen.
- **Paperless (echte Karte):** eine `qsl-card` real ansehen – OCR-Text-Qualität (gedruckt
  vs. handschriftlich), Aufbau Vorder-/Rückseite (zweiseitiges PDF), Bild-Endpunkte testen.
- **Ergebnis:** kurzes Discovery-Doku im Repo (z. B. `docs/discovery.md`) mit den Befunden.
- **Review-Punkt:** Desktop prüft, ob das ermittelte „bestätigt"-Schreibformat plausibel
  und das Papier-QSL-Feld eindeutig ist, BEVOR Schreiblogik gebaut wird.

## Schritt 1 — Repo-Grundgerüst
- Struktur, `.gitignore`, `config.example.yaml`, `README.md`, `CHANGELOG.md`, `LICENSE` (MIT),
  Versions-Datei `0.1.0`, `qsl73-assets/` mit `qsl73logo.png`. Branches `main`/`dev` anlegen.
- **Review:** Vollständigkeit/Struktur, keine Secrets, Version 0.1.0 gesetzt.

## Schritt 2 — Config & Setup-Grundlagen
- Config-Load/Save (`%APPDATA%\QSL73\config.yaml`), DPAPI-Token, Schema-Versionsfeld +
  Migrationsgerüst. Setup-Assistent (Minimalfassung).
- **Review:** Token nur verschlüsselt; fehlende Config → Assistent; Migrationsstub vorhanden.

## Schritt 3 — Paperless-Client
- Auth (Token & User/PW→Token), Dokumente nach Tag holen, OCR-Text, Bild/Preview, Tag PATCH.
- **Review:** liest echte Karten, Bildabruf funktioniert, Fehler bei nicht erreichbarem
  Server werden sauber abgefangen (klare Meldung, kein Crash).

## Schritt 4 — Log4OM-Zugriff (read) + Matching
- DB lesen (WAL), Vorfilter (nur offene Papier-QSL), Parser (Call/Datum/Band/Mode),
  Matching mit Fuzzy=1, Ergebnis sicher/unsicher/kein Match. Noch **kein Schreiben**.
- **Review:** Akzeptanzkriterien §6 (sicher/unsicher/kein Match, Fuzzy an/aus).

## Schritt 5 — Schreiblogik (commit) + Backup
- Sammeln→Vorschau→Bestaetigung("Jetzt schreiben")→eine Transaktion→Tags; Vor-Backup nur
  beim tatsaechlichen Schreiben, Aufbewahrung Default 5. Reihenfolge DB-dann-Tags strikt.
  Auto-Treffer + manuelle Zuordnungen gemeinsam in EINER Transaktion.
- **Review:** Akzeptanzkriterien §5/§7 (Abbruch-Test, Backup-Anzahl, Tag-nur-nach-DB).
  Nebenläufigkeit: SQLITE_BUSY-Handling, Änderungserkennung (data_version/Fallback),
  Pro-QSO-Gegenprüfung, Log4OM-Running-Warnung getestet.

## Schritt 6 — GUI
- Hauptfenster + Log-Ausgabe, Ergebnis-Liste mit Filter, **manueller Zuordnungs-Bildschirm**
  (Kartenanzeige on click, Live-Suche), Fehler-Prompt (aufklappbar), Einstellungen,
  Über/Datenschutz-Dialog, Single-Instance, Icon einbinden.
- **Review:** Akzeptanzkriterien §9; flüssige Liste bei vielen Einträgen.

## Schritt 7 — Logging & Fehler-Reporting
- audit.log/qsl73.log + Rotation; On-demand-Bericht (GitHub-Issue / lokal), bereinigt.
- **Review:** Akzeptanzkriterien §10 (Bericht ohne Secrets).

## Schritt 8 — Update-Lifecycle + Installer/Deinstaller
- GitHub-Releases-Check, Updater, Inno-Installer (still, aufräumend), Deinstaller mit
  Nutzerdaten-Abfrage, Config-Migration scharf schalten.
- **Review:** Akzeptanzkriterien §12/§13.

## Schritt 9 — Build, Test, erstes Release
- PyInstaller-Build (64-Bit), Inno-Setup-Paket, Test auf Win10/11. Versionspflege + CHANGELOG,
  Tag `v0.x.0`, GitHub-Release. Logo/Icon final (Freistellen + .ico durch Claude Code).
- **Review:** Lauf Ende-zu-Ende (Vorschau -> 'Jetzt schreiben') auf echtem System; Release konsistent.

---

## Offene Punkte (laufend)
- Reale OCR-Qualität bei „gemischt" → bestimmt Gewicht des manuellen Workflows.
- Bild-Auflösung für lesbare Handschrift (Preview vs. Original).
- GitHub-Repo-Name unter `kainomatic` final festlegen/prüfen.
