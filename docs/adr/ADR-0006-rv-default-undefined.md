# ADR-0006: RV-Default = "Undefined"; wählbar Bureau/Direct; "Electronic" nicht angeboten

**Status:** Accepted (Vorbehalt: RV-Hand-Test ausstehend, siehe GitHub-Issue)

## Kontext

ADIF definiert QSLVia-Werte: Undefined, Bureau (B), Direct (D), Electronic (E),
Manager (M, nur Import). Für eine Papier-QSL ist „Electronic" fachlich falsch — das
ist der Weg für LOTW/eQSL. Der pauschale RV-Wert soll aus der Nutzer-Konfiguration
kommen, da QSL73 nicht pro Karte weiß, ob sie per Bureau oder direkt kam.

## Entscheidung

- `qsl_route_default` in `config.yaml` (Abschnitt `confirm:`).
- Optionen: `"undefined"` (Default), `"bureau"`, `"direct"`.
- `"electronic"` wird in der UI nicht als Option angeboten.
- Wert gilt pauschal für alle von QSL73 gesetzten Bestätigungen.

## Konsequenzen

- Nutzer kann den Übertragungsweg einmalig konfigurieren, nicht pro Karte überschreiben.
- Default „Undefined" ist sicher (semantisch neutral, kein falscher Wert).
- Fachliche Korrektheit: Electronic bleibt für LOTW/eQSL reserviert.
- Vorbehalt: Exakte Groß-/Kleinschreibung der Log4OM-internen Werte und ob „Undefined"
  sauber akzeptiert wird, ist noch empirisch zu bestätigen (RV-Hand-Test).
