# CLAUDE.md — Arbeits-Briefing für Claude Code

Dieses Dokument beschreibt das Arbeitsvorgehen im QSL73-Projekt.
Es ersetzt **nicht** die fachlichen Dokumente, sondern verweist auf sie.

---

## Projekt

**QSL73** — Windows-Tool, das gescannte QSL-Karten aus Paperless-ngx mit QSOs im
Log4OM-Logbuch abgleicht und Papier-QSL bestätigt. → Details: **KONZEPT.md**

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

| Was | Wo | Wann |
|-----|----|------|
| Designentscheidung (Warum?) | ADR in `docs/adr/` | Bei jeder neuen Grundentscheidung |
| Offene Aufgabe / Bug | GitHub Issue (sinnvoll labeln) | Sofort bei Entdeckung |
| Aufgabe erledigt | Issue schließen | Per `Fixes #N` im Commit |

Format und Nummerierungsschema → `docs/adr/README.md`

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

## Weiterführende Dokumente

| Dokument | Inhalt |
|----------|--------|
| `KONZEPT.md` | Vollständige fachliche Spezifikation |
| `ROADMAP.md` | Schrittplan mit Review-Punkten |
| `docs/discovery.md` | Log4OM-DB-Schema-Befunde (empirisch) |
| `docs/adr/` | Architecture Decision Records |
