# Architecture Decision Records (ADR)

Hier werden Architektur- und Designentscheidungen für QSL73 dauerhaft festgehalten.
Ein ADR dokumentiert **warum** eine Entscheidung so getroffen wurde — nicht nur was.

## Format

```
# ADR-NNNN: Kurztitel

**Status:** Accepted | Superseded by ADR-XXXX

## Kontext
Welches Problem oder welche Anforderung hat die Entscheidung ausgelöst?

## Entscheidung
Was wurde entschieden?

## Konsequenzen
Welche Auswirkungen hat die Entscheidung (positiv und negativ)?
```

## Nummerierungsschema

Dateien: `ADR-NNNN-kurztitel.md` (vierstellig, führende Nullen).  
Nächste freie Nummer: ADR-0051.

## Index

| ADR | Titel |
|-----|-------|
| ADR-0040 | PyInstaller-Build — onedir-Bundle für Windows |
| ADR-0041 | Inno-Setup-Installer für QSL73 (Stable) |
| ADR-0042 | Release-Automatisierung via GitHub Actions + Beta-Installer-Variante |
| ADR-0043 | Versionierung nach Semantic Versioning (MAJOR.MINOR.PATCH) |
| ADR-0044 | Kein Code-Signing — SmartScreen-Warnung dokumentiert statt Zertifikat |
| ADR-0045 | Self-Update-Lifecycle (Kanal-Prüfung, Download-Verifikation, /SILENT-Installer, Opt-out) |
| ADR-0046 | Beta→Stable-Release-Workflow (Versionsnummer, CHANGELOG-Einfrieren, Auslöser-Rollen) |
| ADR-0047 | Hover-Tooltips als einziges UI-Hilfe-Muster (kein Fragezeichen-Icon) |
| ADR-0048 | Stable-Hotfix über `hotfix/*`-Branch von `main` (bei ungereiftem `dev`-Stand) |
| ADR-0049 | Git-Branch-Operationen sind ausschließlich Claude-Code-Aufgabe |
| ADR-0050 | Datenschutz — keine echten fremden Rufzeichen im Repo; fiktive Calls; Historie-Bereinigung zurückgestellt |

## Abgrenzung

- **ADR** = Designentscheidung (bleibt dauerhaft; Superseded statt löschen)
- **GitHub Issue** = offene Aufgabe (wird geschlossen wenn erledigt)
