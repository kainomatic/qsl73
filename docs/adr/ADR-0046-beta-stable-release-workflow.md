# ADR-0046: Beta→Stable-Release-Workflow

**Status:** Accepted

## Kontext

ADR-0021 legt fest, dass es Stable- und Beta-Kanäle gibt. ADR-0042 beschreibt die
Release-Automatisierung via GitHub Actions. ADR-0043 regelt die SemVer-Versionsstellen.

Keine dieser ADRs legt jedoch fest:
- welche Versionsnummer eine Beta trägt,
- wann `__version__.py` gesetzt wird,
- wann der CHANGELOG eingefroren wird,
- wie mehrere Beta-Runden ablaufen,
- wer welches Release auslösen darf.

Diese Lücke führt zu Mehrdeutigkeiten im Release-Prozess und wird hier verbindlich
geschlossen.

## Entscheidung

### 1. Versionsnummer in Beta-Phase

Eine Beta ist die Vorabversion der kommenden Stable-Version. `__version__.py` trägt
**bereits ab der ersten Beta die Ziel-Stable-Nummer** (`X.Y.Z`, ohne Suffix).

Beispiel: main = `v1.2.0`, nächste Stable wird `1.3.0` →
- `__version__ = "1.3.0"` (in `__version__.py`)
- Beta-Tags: `v1.3.0-beta1`, `v1.3.0-beta2`, … (Pre-Releases aus `dev`)
- Stable-Tag: `v1.3.0` (Normal-Release aus `main`)

### 2. Versions-Sync (ADR-0042) mit Beta-Suffix

Der Workflow-Check extrahiert die Basisnummer aus dem Git-Tag via
`'^v(\d+\.\d+\.\d+)'` (kein `$`-Anker) → `v1.3.0-beta1` ergibt Basis `1.3.0`.
Vergleich mit `__version__` (`1.3.0`) → **OK**.

Das Suffix `-betaN` wird vom Regex ignoriert. Kein gesonderter Fix nötig;
das Verhalten ist bereits korrekt und wird hier dokumentiert.

### 3. CHANGELOG — NUR beim Stable-Release einfrieren

Während der gesamten Beta-Phase bleibt der `[Unreleased]`-Block bestehen.
Neue Commits werden weiterhin unter `[Unreleased]` gesammelt.

**Einfrieren (`[Unreleased]` → `[X.Y.Z] - Datum` + neuer leerer `[Unreleased]`)
findet ausschließlich beim Stable-Release statt** — nicht bei Beta-Pre-Releases.

Mehrere Beta-Runden: `-beta2`, `-beta3`, … werden bei Bedarf getaggt;
der CHANGELOG bleibt durchgehend unter `[Unreleased]`.

### 4. Release-Notes-Quelle je Kanal

| Kanal | Quelle im CHANGELOG |
|-------|---------------------|
| Beta (Pre-Release) | `## [Unreleased]` — enthält alle aktuellen Änderungen |
| Stable | `## [X.Y.Z]` — der eingefrorene Abschnitt der fertigen Version |

Der Release-Workflow (`release.yml`) extrahiert kanalabhängig:
- Beta → Regex auf `## [Unreleased]`
- Stable → Regex auf `## [APP_VERSION]` (z. B. `## [1.3.0]`)
- Fallback: `[Unreleased]`, dann Platzhaltertext; kein Workflow-Abbruch.

### 5. Auslöser-Rollen

| Release-Typ | Wer löst aus | Warum |
|-------------|--------------|-------|
| Beta-Pre-Release (`vX.Y.Z-betaN`) | Claude Code (auf Auftrag) | Risikoarm — Stable-Nutzer sehen Pre-Releases nicht; kein main-Eingriff |
| Stable-Release (`vX.Y.Z`, main) | DF1DS manuell | Öffentlich sichtbar; erfordert Desktop-Review und bewusste Entscheidung |

Claude Code darf Beta-Tags setzen und pushen (`git tag vX.Y.Z-betaN && git push origin vX.Y.Z-betaN`).
Den `dev→main`-Merge und den Stable-Tag setzt ausschließlich DF1DS.

### 6. Ablauf Beta-Phase (vollständig)

```
1. __version__.py auf X.Y.Z setzen (Ziel-Stable-Nummer).
2. CHANGELOG NICHT einfrieren — [Unreleased] bleibt.
3. git tag vX.Y.Z-beta1 && git push origin vX.Y.Z-beta1
   → Workflow baut Beta-Installer; Notes aus [Unreleased].
4. Korrekturen/Ergänzungen committen; weiterhin unter [Unreleased].
5. Bei Bedarf: git tag vX.Y.Z-beta2 && git push ... (CHANGELOG unverändert).
```

### 7. Ablauf Stable-Release (nach bewährter Beta oder direkt)

```
1. __version__.py prüfen (muss X.Y.Z enthalten — bei Beta-Phase bereits gesetzt).
   Direktes Stable (ohne Beta): __version__.py jetzt auf X.Y.Z setzen.
2. CHANGELOG einfrieren: [Unreleased] → [X.Y.Z] - YYYY-MM-DD; neuer leerer [Unreleased].
3. Kategorien-Reihenfolge prüfen: Added→Changed→Deprecated→Removed→Fixed→Security.
4. git checkout main && git merge dev && git push origin main
5. git tag vX.Y.Z && git push origin vX.Y.Z
   → Workflow baut Stable-Installer; Notes aus [X.Y.Z].
```

## Konsequenzen

- `__version__.py` zeigt immer die **Ziel-Stable-Nummer** — auch während laufender Beta.
  Das ist bewusst: `"0.2.0"` in der App, aber Tag `v0.2.0-beta1` auf dem Commit.
- Der `[Unreleased]`-Block wächst über die gesamte Beta-Phase und enthält beim
  Stable-Release den vollen Änderungsumfang.
- Das Einfrieren geschieht genau einmal pro Stable-Release — deterministisch, kein
  „wann genau"-Spielraum.
- Mehrere Betas sind explizit unterstützt; jede bekommt einen eigenen Tag, kein Rebasing.
- Beta-Releases sind Pre-Releases auf GitHub → nicht im Stable-Update-Check sichtbar
  (ADR-0045 filtert nach Kanal).
