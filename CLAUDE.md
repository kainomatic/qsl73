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

## Arbeits- und Review-Schleife

```
Desktop spezifiziert Auftrag (Kontext + Aufgabe + Akzeptanzkriterien)
  → DF1DS überbringt an Claude Code
    → Claude Code baut, committet, meldet zurück
      → Desktop liest Repo und reviewt gegen Akzeptanzkriterien
        → Korrektur-Auftrag oder Freigabe
          → nächster Schritt
```

**Immer nur ein Auftrag gleichzeitig aktiv.** Nicht parallel am Repo arbeiten.

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

---

## Weiterführende Dokumente

| Dokument | Inhalt |
|----------|--------|
| `KONZEPT.md` | Vollständige fachliche Spezifikation |
| `ROADMAP.md` | Schrittplan mit Review-Punkten |
| `docs/discovery.md` | Log4OM-DB-Schema-Befunde (empirisch) |
| `docs/adr/` | Architecture Decision Records |
