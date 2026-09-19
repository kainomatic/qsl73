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
Nächste freie Nummer: ADR-0065.

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
| ADR-0051 | QR-Verlagerung in manuellen Dialog + RAM-Byte-Cache (PdfByteCache, Prefetch) |
| ADR-0052 | Treeview-Klick-Sortierung + Live-Textsuche im Hauptfenster |
| ADR-0053 | Durchlauf-Abbruch in der Lesephase (cancel_event-Mechanik, Button-Umwandlung, Teilergebnis) |
| ADR-0054 | Beta-Self-Update — volle Pre-Release-Version im Build + numerischer betaN-Vergleich |
| ADR-0055 | Log-Level im Einstellungen-Dialog (app.log_level) |
| ADR-0056 | Matching bei mehreren Fremdcalls + Fuzzy erzwingt UNSICHER (Issue #33 Teil 2, verschärft ADR-0016) |
| ADR-0057 | Bindestrich-Datumsformate TT-MM-JJJJ/TT-MM-JJ mit >12-Disambiguierung |
| ADR-0058 | Erklärbarkeit der Matching-Entscheidung (MatchReason) — Engine liefert Grund als Daten, GUI rendert ihn |
| ADR-0059 | Karten ignorieren — ersetzt den ungenutzten Unsicher-Tag (tags.ignored, sofortige Wirkung, kein DB-Zugriff) |
| ADR-0060 | ADR-Zeitpunkt bei nur vorgemerkten Features — Entscheidungen zunächst im Issue, ADR erst mit dem ersten Umsetzungsauftrag |
| ADR-0061 | ROADMAP — Zweck und Struktur (nur Stand + priorisierte nächste Schritte, keine Issue-Liste, keine Änderungs-Historie) |
| ADR-0062 | GUI-Tests nutzen einen session-weiten tk-Root (ein `tk.Tk()` pro Testprozess statt hunderter Einzel-Erzeugungen, Issue #40) |
| ADR-0063 | Update-Prüfung nutzt Queue-Polling statt cross-thread `self.after` (RunController.start_update_check + UpdateCheckDoneEvent, Issue #40) |
| ADR-0064 | Eingangs-Tag als Arbeitskorb — Entfernen bei Bestätigen/Ignorieren (ein PATCH je Aktion), einmalige Alt-Bestand-Abfrage + dauerhafter Menüpunkt (Issue #41) |

## Abgrenzung

- **ADR** = Designentscheidung (bleibt dauerhaft; Superseded statt löschen)
- **GitHub Issue** = offene Aufgabe (wird geschlossen wenn erledigt)
