# CLAUDE.md — Arbeits-Briefing für Claude Code

Dieses Dokument beschreibt das Arbeitsvorgehen im QSL73-Projekt.
Es ersetzt **nicht** die fachlichen Dokumente, sondern verweist auf sie.

---

## Projekt

**QSL73** — Windows-Tool, das gescannte QSL-Karten aus Paperless-ngx mit QSOs im
Log4OM-Logbuch abgleicht und Papier-QSL bestätigt. → Details: **KONZEPT.md**

---

## Onboarding für neue Sessions

**Der Chatverlauf ist flüchtig. Das Repo ist die maßgebliche Wahrheit.**

Zu Beginn jeder neuen Session diese Dateien in dieser Reihenfolge lesen:

1. `CLAUDE.md` — Arbeitsvorgehen (dieses Dokument)
2. `ROADMAP.md` — aktueller Schritt und Review-Stand
3. `KONZEPT.md` — Spezifikation (bei Bedarf; bei Codearbeit immer)
4. `docs/adr/` — getroffene Designentscheidungen
5. `docs/discovery.md` — Log4OM-DB-Befunde (bei DB-naher Arbeit)

Gilt für beide Claude-Instanzen: Claude Code liest `CLAUDE.md` automatisch beim Start;
Claude Desktop wird über seine Projekt-Anweisungen hierher verwiesen.

---

## Rollenmodell

| Rolle | Wer | Aufgabe |
|-------|-----|---------|
| **Architekt & Reviewer** | Claude Desktop | Liest Repo **read-only** (Filesystem-Tool); schreibt KONZEPT.md und Auftrags-Prompts; reviewt jeden Schritt gegen Akzeptanzkriterien. Commitet **nie** direkt. |
| **Vermittler** | DF1DS | Überbringt Prompts und Repo-Stände zwischen Desktop und Claude Code; führt manuelle Schritte in Log4OM und Paperless aus. |
| **Ausführender Maintainer** | Claude Code | Alleiniger Entwickler: Code, Commits, Tests, GitHub, Versionierung, Releases, Doku. |

---

## Branch-Strategie

- `main` — stabile Releases (nur für Releases aktualisieren)
- `dev` — laufende Entwicklung; **Standard-Arbeitsbranch**
- `feature/*` — zweigen von `dev` ab, werden nach `dev` gemergt

**Regel:** Standardmäßig auf `dev` committen. `main` nur bei Releases.

---

## Pflicht-Pfad

Das Repo **muss** unter `C:\Entwicklung\qsl73` liegen.
Claude Desktop greift per Filesystem lesend auf genau diesen Pfad zu. Anderen Pfad
verwenden bedeutet: Reviewer kann nicht reviewen.

---

## Sessions / Clear

**Zuständigkeiten:**
- **Claude Desktop entscheidet**, ob ein Auftrag eine neue Session erfordert, und gibt den
  Hinweis `NEUE SESSION: ja` oder `NEUE SESSION: nein` am Anfang des Auftrags.
- **DF1DS (User) führt `/clear` aus** — vor dem Einfügen des Auftrags in Claude Code, wenn
  `NEUE SESSION: ja` gesetzt ist. `/clear` ist ein Bedienelement der Claude-Code-Oberfläche;
  Claude Code kann seine eigene Session nicht selbst leeren.
- **Claude Code** beginnt dadurch mit frischem Kontext und liest die Onboarding-Dateien
  (`CLAUDE.md`, `KONZEPT.md`, `ROADMAP.md` usw.) neu ein — gemäß Abschnitt
  „Onboarding für neue Sessions".
- Bei `NEUE SESSION: nein` wird der Auftrag in der laufenden Session fortgeführt.

**Faustregel für Desktop:**
- **Neue Session:** beim Start eines neuen, thematisch eigenständigen Bau-Schritts
  (z. B. ROADMAP-Schritt-Grenzen wie „jetzt Schritt 3").
- **Session fortführen:** bei Folge-Korrekturen oder Ergänzungen innerhalb desselben Themas
  (z. B. Review-Feedback zum laufenden Schritt, kleine Doku-Nachbesserungen).

**Begründung:** hält den Kontext fokussiert und vermeidet Kontextverschmutzung durch
ältere Zwischenstände. Gefahrlos, weil der maßgebliche Stand vollständig im Repo liegt
(`CLAUDE.md`, `KONZEPT.md`, `ROADMAP.md`, `docs/adr/`, GitHub-Issues) und nach einem Clear
über das Onboarding-Verfahren neu eingelesen wird.

---

## Arbeits- und Review-Schleife

```
Desktop spezifiziert Auftrag (Kontext + Aufgabe + Akzeptanzkriterien)
  → DF1DS überbringt an Claude Code
    → Claude Code baut, committet, pusht nach origin/dev, meldet zurück
      → Desktop liest Repo und reviewt gegen Akzeptanzkriterien
        → Korrektur-Auftrag oder Freigabe
          → nächster Schritt
```

**Immer nur ein Auftrag gleichzeitig aktiv.** Nicht parallel am Repo arbeiten.

---

## Definition of Done je Bau-Schritt

Ein Schritt (oder Teilschritt) gilt erst als **fertig**, wenn alle sechs Punkte erfüllt
sind. → Begründung und Kontext: **ADR-0027**

| # | Kriterium | Wie |
|---|-----------|-----|
| 1 | **pytest grün** (lokal) + **CI grün** (GitHub Actions) | Pflicht ab Schritt 2; Teststrategie → ADR-0009 |
| 2 | **ROADMAP.md-Status** des Schritts/Teilschritts aktualisiert | `✅` abgeschlossen / `➡️` nächster Schritt / `🔧 IN ARBEIT` |
| 3 | **CHANGELOG.md `[Unreleased]`** um die Änderung ergänzt | Unter passendem Abschnitt (`### Added` / `### Fixed` / …) |
| 4 | **Zugehörige GitHub-Issues geschlossen** | Bevorzugt per `Fixes #N` im Commit; sonst mit Schließkommentar inkl. belegendem Commit-Hash. Issue nur schließen wenn Fix im Code belegt. |
| 5 | **ADR angelegt**, falls im Schritt eine Design-/Grundentscheidung gefallen ist | → bestehende ADR-Pflicht (Abschnitt „Entscheidungen und Aufgaben festhalten") |
| 6 | **Nach `origin` gepusht** (`git push origin dev`) **+ `origin/dev`-Hash im Bericht genannt** | `git log --oneline -1 origin/dev` → Hash im Abschluss-Bericht. „working tree clean" allein genügt nicht. → ADR-0027 |

**Hinweis:** Diese Checkliste ergänzt die ADR-Pflicht und ADR-0009 — sie ersetzt sie nicht.
Punkte 1 und 5 sind bereits anderweitig verankert; die Liste macht alle sechs Kriterien an
einer Stelle sichtbar, damit kein Punkt beim Schritt-Abschluss vergessen wird.

**Routinemäßiges Pushen auf `dev` ist unkritisch und erwünscht.** Die Update-Prüfung der
App richtet sich gegen `main`-Releases und explizit getaggte Pre-Releases (→ ADR-0021),
nicht gegen jeden `dev`-Push. Es besteht kein Grund, mit dem Push zu warten.

---

## Entscheidungen und Aufgaben festhalten

### ADR-Pflicht (verbindlich)

Jede **Design- oder Grundentscheidung** — Architektur, Datenformat, Konfliktverhalten,
Sicherheitsmodell, Verhaltensregel — **muss** als ADR in `docs/adr/` festgehalten werden.

**Auslöser:** Fällt im Planungsgespräch eine solche Entscheidung, enthält der zugehörige
oder nächste Auftrag an Claude Code standardmäßig den Punkt „dazu ein ADR anlegen".
ADR-Erstellung ist **Standard**, nicht Ausnahme.

**Nicht als ADR:** Tippfehler, Kosmetik, einzelne Aufgaben → das sind GitHub Issues.

**ADR-Lebenszyklus:** Status `Accepted` beim Anlegen; bei Revision auf `Superseded by ADR-XXXX`
setzen — niemals löschen. Format und Nummerierung → `docs/adr/README.md`

### Aufgaben und Bugs

| Was | Wo | Wann |
|-----|----|------|
| Design-/Grundentscheidung | ADR in `docs/adr/` | Standardmäßig bei jeder Entscheidung |
| Offene Aufgabe / Bug | GitHub Issue (sinnvoll labeln) | Sofort bei Entdeckung |
| Aufgabe erledigt | Issue schließen | Per `Fixes #N` im Commit |

---

## Sicherheits- und Datenschutz-Leitplanken

- **Niemals ins Repo:** Tokens, Passwörter, URLs mit Zugangsdaten, echte Log4OM-DB,
  QSL-Karten. `docs/testdateien/` und `*.sqlite`/`*.db` sind per `.gitignore` gesperrt —
  diese Regeln nicht entfernen oder umgehen.
- **Nur 3 erlaubte Verbindungen:** eigenes Paperless-ngx, lokale Log4OM-DB (kein Netz),
  GitHub (nur für Update-Prüfung). Keine Telemetrie, kein „nach Hause telefonieren".
- **Schreibzugriffe auf Log4OM-DB** ausschließlich gemäß KONZEPT.md §3.3 + §7:
  Schema-Check → WAL → Vor-Backup → eine Transaktion → erst nach Nutzerbestätigung.

---

## Versionierung

- SemVer `MAJOR.MINOR.PATCH`; einzige Versions-Quelle: `src/qsl73/__version__.py`
- `CHANGELOG.md` bei jedem Release pflegen
- Eingebaute Version = Git-Tag = GitHub-Release — alle drei immer konsistent halten

### Versionsregel (ADR-0043)

| Stelle | Wann erhöhen |
|--------|-------------|
| **MAJOR** | Inkompatible Änderung — Config-Schema-Bruch (alte `config.yaml` lädt nicht), Schreibformat-Inkompatibilität in Log4OM-DB, Entfernen zentraler Felder/Funktionen. |
| **MINOR** | Neue Funktion, abwärtskompatibel — bestehende Config und DB-Daten laufen unverändert weiter. |
| **PATCH** | Bugfix oder kleine Verbesserung — kein neues Verhalten, keine Schema-/Format-Änderung. |

**Faustregel:** Im Zweifel MINOR für Features, PATCH für Fixes. MAJOR nur bei echter
Inkompatibilität. Solange MAJOR=0 (aktuell), können Breaking Changes auch in MINOR
vorkommen (Pre-1.0-Ausnahme; ab 1.0.0 gilt SemVer strikt).

### CHANGELOG-Release-Handgriff (ADR-0046)

`[Unreleased]` ist die laufende Sammelstelle. **Einfrieren NUR beim Stable-Release** —
nicht bei Beta-Pre-Releases. → vollständiger Workflow: **ADR-0046**

#### Beta-Release (Pre-Release — Claude Code darf auslösen)

1. **Version setzen** (falls noch nicht): `__version__.py` auf `X.Y.Z` (Ziel-Stable-Nummer).
   `CHANNEL` bleibt `"stable"` — Kanal-Patch erfolgt ephemer im Release-Workflow.
2. **CHANGELOG NICHT einfrieren.** `[Unreleased]` bleibt bestehen; neue Einträge weiter dort.
3. **Tag setzen und pushen:** `git tag vX.Y.Z-betaN && git push origin vX.Y.Z-betaN`
   → Workflow baut Beta-Installer; Release-Notes aus `[Unreleased]`.
4. Mehrere Runden: `-beta2`, `-beta3`, … bei Bedarf; `[Unreleased]` wächst weiter.

#### Stable-Release (DF1DS manuell nach Desktop-Review)

1. **Version prüfen:** `__version__.py` muss `X.Y.Z` enthalten (aus Beta-Phase bereits gesetzt;
   bei Direktrelease ohne Beta jetzt setzen).
2. **`[Unreleased]` einfrieren:** umbenennen in `## [X.Y.Z] - YYYY-MM-DD` (ISO 8601).
3. **Neuen `[Unreleased]`-Block** direkt darüber anlegen — leere Sammelstelle.
4. **Kategorien-Konvention prüfen:** `Added → Changed → Deprecated → Removed → Fixed → Security`
   (Keep-a-Changelog-Standard); leere Kategorien weglassen; mehrere gleichnamige Blöcke zusammenführen.
5. **`dev → main` mergen:** `git checkout main && git merge dev && git push origin main`
6. **Tag setzen und pushen:** `git tag vX.Y.Z && git push origin vX.Y.Z`
   → Workflow baut Stable-Installer; Release-Notes aus `[X.Y.Z]`.

### Welche Stelle bei gemischten Änderungen? Wer entscheidet?

Bei einem Release mit **gemischten Änderungen** bestimmt die **höchstwertige** betroffene
Stelle die Versionsnummer — MAJOR schlägt MINOR schlägt PATCH:

| Situation | Stelle |
|-----------|--------|
| Inkompatible Änderung dabei (Config-Schema-Bruch, DB-Format-Bruch) | **MAJOR** |
| Mind. ein neues Feature, kein Bruch | **MINOR** (Fixes fahren mit, kein Extra-PATCH) |
| Nur Bugfixes/Kosmetik, kein Feature, kein Bruch | **PATCH** |

Alle zwischen zwei Stable-Releases gesammelten Änderungen gehen in **ein** Stable-Release;
nicht erst PATCH für Fixes, dann MINOR für Features — der `[Unreleased]`-Block wird
beim Stable-Release vollständig eingefroren.

**Wer entscheidet:** Der Maintainer (DF1DS) beim Stable-Release. Entscheidungsgrundlage ist die
`[Unreleased]`-Liste im CHANGELOG:
- Etwas unter `Added` → mindestens MINOR
- Schema- oder Format-Bruch unter `Changed`/`Removed` → MAJOR
- Nur `Fixed`/`Security`/Kosmetik → PATCH

**Rolle Claude Desktop:** Schlägt vor dem Stable-Release die Versionsnummer anhand der
`[Unreleased]`-Kategorien vor und begründet die Wahl; DF1DS bestätigt oder korrigiert.
Desktop erklärt vor jedem Stable-Release ausdrücklich die geplanten Schritte (Versionsnummer,
CHANGELOG-Einfrieren, dev→main-Merge, Tag), **bevor** der Release-Auftrag an Claude Code
geht — kein stilles Vorgehen über den Kopf des Maintainers hinweg.

---

## Testen

**Ab Schritt 2 (erster Anwendungscode) sind Unit-Tests Pflicht** — ein Schritt ist erst
fertig, wenn seine Tests grün sind. → Details und Begründung: **ADR-0009**

- **Framework:** `pytest`
- **CI:** GitHub Actions läuft bei jedem Push auf `dev` und `main` automatisch
- **Schreibtests:** ausschließlich gegen eine temporäre Wegwerf-Kopie der Test-DB —
  niemals gegen echte Daten; `docs/testdateien/` bleibt `.gitignore`-gesperrt
- **CI-DB:** synthetische Minimal-DB (kein Zugriff auf `docs/testdateien/` im CI)

### Erwartetes Skip-Muster (DPAPI-Tests) — kein Fehler

| Umgebung | DPAPI-Round-Trip-Tests | fail-closed-Sicherheitstest |
|----------|------------------------|------------------------------|
| Windows-Dev **mit** pywin32 | **passed** (laufen real durch) | skipped (pywin32 vorhanden) |
| Windows-Dev **ohne** pywin32 | skipped | **passed** |
| CI (Linux, ohne pywin32) | skipped | **passed** |

Skips in diesen Kombinationen sind **erwartet und kein Reparaturanlass**. Nur ein
unerwarteter Skip (z. B. DPAPI-Test skippt obwohl pywin32 laut `pip list` installiert ist)
wäre ein echtes Problem. Stand Dev-Maschine: pywin32 installiert → 3 Skips erwartet
(Linux-only-Test + 2× "Windows-ohne-pywin32"-Sicherheitstests).

### Test-Ausführung — Tool-Wahl und Laufzeiten

**Bash bevorzugen, nicht PowerShell** — das PowerShell-Tool hat ein kurzes internes
Timeout und kennt kein `tail`; pytest-Läufe > ~5 s brechen mit Exit 137 (OS-Kill) ab.
Exit 137 in diesem Kontext ist ein Tool-Timeout, kein Test-Fehler.

| Lauf | Befehl | Wann |
|------|--------|------|
| Schnell (Zwischenlauf) | `pytest -m "not slow"` | Jederzeit während der Entwicklung |
| Vollständig (Pflicht) | `pytest` | Vor jedem Schritt-Abschluss (DoD, ADR-0027) |

Die Acceptance-Tests (`tests/acceptance/`) tragen den Marker `slow` und brauchen ~25 s
(DB-Kopie-Läufe). Der schnelle Zwischenlauf überspringt sie; der vollständige grüne Lauf
bleibt Pflicht laut Definition of Done — `-m "not slow"` ersetzt ihn nicht.

`pytest-timeout` setzt ein Default-Timeout von 60 s pro Test, damit ein hängender
einzelner Test gezielt fehlschlägt statt die gesamte Suite zu killen.

---

## Weiterführende Dokumente

| Dokument | Inhalt |
|----------|--------|
| `KONZEPT.md` | Vollständige fachliche Spezifikation |
| `ROADMAP.md` | Schrittplan mit Review-Punkten |
| `docs/discovery.md` | Log4OM-DB-Schema-Befunde (empirisch) |
| `docs/adr/` | Architecture Decision Records |
