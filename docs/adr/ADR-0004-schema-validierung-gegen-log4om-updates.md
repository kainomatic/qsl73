# ADR-0004: Schema-Validierung gegen Log4OM-Strukturänderungen

**Status:** Accepted

## Kontext

Das `qsoconfirmations`-Format (JSON-Array mit CT/R/RD/RV) ist eine undokumentierte
Log4OM-Interna. Ein Log4OM-Update könnte Tabelle, Spalte oder JSON-Struktur umbenennen.
QSL73 darf dann nicht blind schreiben — das würde die DB korrumpieren.

## Entscheidung

- Schema-Check **beim Programmstart** und **direkt vor jedem Schreibvorgang**.
- Geprüft wird: Tabelle `Log` vorhanden? Spalte `qsoconfirmations` vorhanden? JSON parsebar
  mit erwarteten Feldern (CT, R, RD, RV)?
- **Bei Abweichung:** Schreiben gesperrt; Lesen/Anzeigen bleibt möglich; klare Meldung an
  Nutzer; `qsl73.log` vermerkt exakt, was abweicht.
- Abgrenzung: §7 (KONZEPT) schützt vor DATEN-Änderungen zur Laufzeit; §3.3 schützt vor
  STRUKTUR-Änderungen durch Updates.

## Konsequenzen

- Robustheit gegen zukünftige Log4OM-Versionen ohne sofortigen Anwendungs-Crash.
- Nutzer erhält klaren Handlungshinweis (auf QSL73-Update prüfen).
- Lesebetrieb (Anzeigen, Suchen) bleibt auch bei unbekanntem Schema so weit möglich.
