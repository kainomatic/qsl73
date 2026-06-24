# ADR-0054: Beta-Self-Update — volle Pre-Release-Version im Build + numerischer betaN-Vergleich

**Status:** Accepted

## Kontext

Issue #27: Eine laufende v0.3.0-beta1 erkannte eine veröffentlichte v0.3.0-beta2 nicht als
Update. Diagnose ergab zwei unabhängige Bugs:

**BUG 1** (Hauptursache): `release.yml` patchte beim Beta-Build nur `CHANNEL` ("stable"→"beta"),
nicht aber `__version__`. Die laufende Beta meldete daher `current_version = "0.3.0"` (ohne
-betaN). In `semver_gt` griff der Zweig `curr_pre == "" and cand_pre != "" → return False`
("stable ≥ jede beta derselben Basis") und wies beta2 als "nicht neuer" ab.

**BUG 2** (latent): Selbst mit korrekt befülltem `current_version = "0.3.0-beta2"` verglich
`semver_gt` die letzte Zeile `return cand_pre > curr_pre` lexikografisch. Damit ist
`"beta2" > "beta10"` lexikografisch True → beta10 würde nicht als neuer erkannt. Dasselbe
Problem steckte im `_sort_key` von `_find_best_release`.

## Entscheidung

### BUG 1 — Option A: Workflow patcht `__version__` ephemer

In `.github/workflows/release.yml` wird Schritt 7 (bisheriger CHANNEL-Patch) um einen zweiten
Patch ergänzt: Beim Beta-Build wird `__version__` von der Stable-Basis-Nummer (`"0.3.0"`) auf
die volle Tag-Version (`"0.3.0-beta2"`) gesetzt — ausschließlich im CI-Lauf, kein Commit.

Die volle Tag-Version wird aus `github.ref_name` abgeleitet (führendes "v" entfernen):
`$fullVer = "${{ github.ref_name }}".TrimStart('v')`

Option B (separate `_build_meta.py`) wurde verworfen: Sie hätte eine neue Importkette in
`updater.py`, einen zusätzlichen CI-Pfad zum Erzeugen der Datei und eine gesonderte
Installations-Infrastruktur erfordert — mehr Komplexität für denselben Effekt.

**Versions-Sync-Check (Schritt 3) bleibt unverändert gültig:** Er prüft nur die X.Y.Z-Basis
(`$tagVer = $Matches[1]` nach `^v(\d+\.\d+\.\d+)`) gegen `__version__.py`. Da der Patch in
Schritt 7 NACH Schritt 3 erfolgt, sieht der Sync-Check den ursprünglichen Wert. Diese
Reihenfolge ist beabsichtigt und stabil.

Stable-Build bleibt unverändert (kein Versions-Patch).

### BUG 2 — numerischer betaN-Vergleich via `_pre_sort_key`

Neue Hilfsfunktion `_pre_sort_key(pre: str) -> tuple` in `updater.py`:

| Eingabe          | Schlüssel          | Bedeutung                                      |
|------------------|--------------------|------------------------------------------------|
| `""` (stable)    | `(1, 0, "")`       | Größer als jede beta                           |
| `"betaN"` (beta) | `(0, N, "")`       | Numerisch nach N; beta10 > beta2               |
| anderes Suffix   | `(-1, 0, pre)`     | Unterhalb aller betaN; lexikografisch untereinander (Fallback) |

Die Funktion ersetzt in `semver_gt` die letzte Zeile
`return cand_pre > curr_pre` durch `return _pre_sort_key(cand_pre) > _pre_sort_key(curr_pre)`.

In `_find_best_release._sort_key` ersetzt der Rückgabewert `("\xff" if pre == "" else pre)` den
String-Teil durch `_pre_sort_key(pre)` — DRY-Prinzip, beide Stellen nutzen dieselbe Logik.

**Fallback für unbekannte Suffixe:** Ein Suffix wie "rc1", das nicht dem Schema `beta\d+`
entspricht, ergibt `(-1, 0, "rc1")`. Es sortiert unterhalb jedes betaN und stürzt nicht ab.
Zwei unbekannte Suffixe werden lexikografisch nach ihrem String-Wert sortiert. Das Projekt
nutzt ausschließlich `betaN` — der Fallback ist dokumentiert, aber im Normalbetrieb nie aktiv.

## Konsequenzen

- Laufende Beta meldet nach dem Fix `current_version = "0.3.0-beta2"` und erkennt ein
  veröffentlichtes `v0.3.0-beta10` korrekt als neuer (Issue #27 geschlossen).
- `beta10 > beta2` gilt jetzt auch für `_find_best_release`: der Best-Release wird korrekt
  gewählt, wenn mehrere Betas derselben Basis vorliegen.
- Stable-Build, Versions-Sync-Check und `__version__.py` im Repo bleiben unverändert.
- Bezug: ADR-0045 (Self-Update-Lifecycle), ADR-0046 (Beta→Stable-Workflow),
  ADR-0021 (Release-Kanäle), ADR-0043 (SemVer).
