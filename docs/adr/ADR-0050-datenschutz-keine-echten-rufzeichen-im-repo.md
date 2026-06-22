# ADR-0050: Datenschutz — keine echten fremden Rufzeichen im Repo; fiktive Calls; Historie-Bereinigung zurückgestellt

**Status:** Accepted

## Kontext

Beim Aufbau von Test-Fixtures und Beispiel-Dokumentation wurden echte Amateurfunk-Rufzeichen
(DH3KR, DK8NE, DG5MLA, OE6DRG, G7JVJ u. a.) aus realen Test-QSL-Karten direkt in
versionierte Dateien übernommen — Testdaten, Parameterwerte, Kommentare, ADRs, CHANGELOG.

**Datenschutzproblem:** Rufzeichen sind über die öffentliche BNetzA-Rufzeichenliste
eindeutig natürlichen Personen zuordenbar (Name, Anschrift). Die Veröffentlichung im
öffentlichen GitHub-Repo entspricht nicht dem Zweck des ursprünglichen Funkkontakts
(ITU-Regulierung, DSGVO-Grundsatz der Zweckbindung). Eine Einwilligung der betroffenen
Funkamateure liegt nicht vor.

Betroffen waren getrackter Code und Dokumentation auf beiden öffentlichen Branches (`dev`
und `main`). Nicht betroffen: lokal abgelegte Dateien, die `.gitignore`-gesperrt sind
(echte Log4OM-DBs, QSL-PDFs in `docs/testdateien/`, `config.yaml`, `*.sqlite`).

## Entscheidung

### Fake-Call-Konvention (dauerhaft)

In versionierten Dateien sind ausschließlich folgende Rufzeichen erlaubt:

- **Eigenes Call:** `DF1DS` (Autor, Maintainer)
- **Fiktive Test-Calls:** Calls mit klar fiktivem Suffix `XXX`, `AA`, `BB` o. ä., z. B.:
  `DL0AAA`, `DK8XX`, `DK8XY`, `DG5XXX`, `OE6XXX`, `G7XXX`, `DL1XXX`, `UA4XXX`, …

Diese Konvention ist in `CLAUDE.md` (Abschnitt „Sicherheits- und Datenschutz-Leitplanken")
verankert und gilt für alle zukünftigen Commits.

### Bereinigung des aktuellen Standes (durchgeführt)

- Alle echten fremden Rufzeichen in getrackten Dateien wurden durch fiktive Calls ersetzt.
- Mapping: DH3KR→DL0AAA, DK8NE→DK8XX, DK8NF→DK8XY, DG5MLA→DG5XXX, OE6DRG→OE6XXX,
  G7JVJ→G7XXX, TM2CIN→TM2XXX, WB1CLT→WB1XXX, DN9MF→DN9XX, DL1EJD→DL1XXX,
  UA4WHX→UA4XXX, DO6KBO→DO6XXX.
- Hashes nach Bereinigung: `dev` = 3b1964a, `main` = 683b8ff.

### Git-Historie-Bereinigung (Option, bewusst zurückgestellt)

Die alten Commits auf beiden Branches enthalten die echten Calls weiterhin in der
**Git-Historie** (einsehbar via `git log -p` oder GitHub-Commit-Ansicht für Klonende).

**Entscheidung:** Die Historie-Bereinigung wird bewusst zurückgestellt. Das primäre
Schutzziel ist bereits erreicht:

1. Der **aktuelle Repo-Stand** (alle Branches/Tags ab den Bereinigungscommits) ist frei
   von echten fremden Rufzeichen.
2. Der **ausgelieferte Installer** enthält keine Git-Historie — wer die App installiert,
   kann die alten Commits nicht einsehen.

Das verbleibende Restrisiko (alte Commits/Tags auf GitHub für Repo-Klonende einsehbar)
wird von DF1DS bewusst akzeptiert. Eine weitere Reduktion dieses Risikos wäre nur durch
den invasiven History-Rewrite erreichbar, dessen Aufwand und Nebenwirkungen unverhältnismäßig
sind (siehe unten).

**Nachhol-Option:** Die Bereinigung kann jederzeit nachgeholt werden, falls sich das
Schutzbedürfnis ändert (z. B. bei Hinweisen von Betroffenen). Dazu nötige Schritte:

1. `git filter-repo --path-glob '*' --replace-text <ersetzungsdatei>` (oder BFG Repo Cleaner)
   — rewrite der gesamten History auf beiden Branches.
2. Force-Push auf `origin/main` und `origin/dev`; alle GitHub-Tags löschen und neu setzen.
3. Alle lokalen Klone müssen danach neu geklont oder per `git fetch --all && git reset --hard`
   angeglichen werden (bestehende Klone werden durch den Rewrite inkonsistent).
4. Repo-Backup vor dem Rewrite ist Pflicht.
5. Explizite Freigabe durch DF1DS erforderlich (Breaking Change für alle Klones/Forks).

### Installer und generierte Dokumentation (überprüft, sauber)

- `installer/qsl73.iss` und `installer/qsl73-beta.iss`: enthalten ausschließlich `DF1DS`,
  GUIDs, Pfade und URLs — keine fremden Calls.
- `installer/docs/` (generierte HTML-Doku): per `.gitignore` ausgeschlossen; wird beim
  Build aus den Markdown-Quellen generiert → erbt automatisch den bereinigten Stand.

## Konsequenzen

- **Datenschutzkonform:** Keine personenbezogenen Rufzeichen mehr im öffentlichen Repo-Stand.
- **Konvention muss eingehalten werden:** Jeder zukünftige Commit darf nur `DF1DS` oder
  klar fiktive Calls enthalten. Claude Code und Claude Desktop prüfen dies vor Commits.
- **Restrisiko Git-Historie (akzeptiert):** Alte Calls stehen in der Geschichte; für
  Repo-Klonende einsehbar via `git log -p`. Schutzziel ist durch bereinigten aktuellen Stand
  und Installer-ohne-Historie bereits erfüllt. Rewrite bleibt Nachhol-Option (→ oben).
- **Kein Release ausgelöst:** Die Bereinigung betrifft ausschließlich Doku/Tests, nicht den
  ausgelieferten Installer — kein v0.2.4 nötig.

## Verweise

- `CLAUDE.md` → Abschnitt „Sicherheits- und Datenschutz-Leitplanken" (Fake-Call-Konvention)
- `.gitignore` → Ausschluss sensibler Lokaldaten (docs/testdateien/, *.sqlite, config.yaml)
- ADR-0048, ADR-0049 → Hotfix-/Branch-Operationsregeln (Bereinigung lief via
  `hotfix/callsign-cleanup` von main, danach Rück-Merge nach dev)
