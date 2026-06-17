# ADR-0006: RV-Default = "Undefined"; wählbar Bureau/Direct; "Electronic" nicht angeboten

**Status:** Accepted

## Kontext

ADIF definiert QSLVia-Werte: Undefined, Bureau (B), Direct (D), Electronic (E),
Manager (M, nur Import). Für eine Papier-QSL ist „Electronic" fachlich falsch — das
ist der Weg für LOTW/eQSL. Der pauschale RV-Wert soll aus der Nutzer-Konfiguration
kommen, da QSL73 nicht pro Karte weiß, ob sie per Bureau oder direkt kam.

Der RV-Hand-Test (2026-06-17) hat die exakte Schreibweise der Log4OM-internen Werte
und das Verhalten bei „Undefined" empirisch bestätigt (Issue #1 geschlossen).

## Entscheidung

- `qsl_route_default` in `config.yaml` (Abschnitt `confirm:`).
- Optionen: `"undefined"` (Default), `"bureau"`, `"direct"`.
- `"electronic"` wird in der UI nicht als Option angeboten.
- Wert gilt pauschal für alle von QSL73 gesetzten Bestätigungen.

**Mapping Config → Log4OM (empirisch bestätigt):**

| Config-Wert | Log4OM schreibt | Befund |
|-------------|-----------------|--------|
| `"bureau"` | `"RV":"Bureau"` | Großer Anfangsbuchstabe (kein `"bureau"`) |
| `"direct"` | `"RV":"Direct"` | Großer Anfangsbuchstabe (kein `"direct"`) |
| `"undefined"` | RV-Feld **entfernen** | Log4OM schreibt keinen `"Undefined"`-Wert; der Schlüssel `RV` wird aus dem JSON-Objekt vollständig entfernt. Ein vorhandener Wert (z. B. `"Electronic"`) wird dabei überschrieben/entfernt. |

## Konsequenzen

- Nutzer kann den Übertragungsweg einmalig konfigurieren, nicht pro Karte überschreiben.
- Default „Undefined" ist sicher (semantisch neutral; RV-Feld wird entfernt, kein falscher Wert).
- Fachliche Korrektheit: Electronic bleibt für LOTW/eQSL reserviert.
- Implementierung in Schritt 5: Config-Wert muss beim Schreiben korrekt gemappt werden
  (`"bureau"` → `"Bureau"`, `"direct"` → `"Direct"`, `"undefined"` → `del entry["RV"]`).
