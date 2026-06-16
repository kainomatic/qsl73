# ADR-0002: Schreibmodell — Vorschau + Bestätigung (kein separater dry-run)

**Status:** Accepted

## Kontext

Zwei Varianten wurden evaluiert:
- **Variante A:** Separater dry-run-Modus zeigt geplante Änderungen; danach explizit
  Commit-Modus starten.
- **Variante B:** Ein einziger Lauf mit eingebetteter Vorschau; Schreiben erst nach Klick
  „Jetzt schreiben".

## Entscheidung

Variante B. Kein separater dry-run. Jeder Lauf zeigt zuerst die vollständige Vorschau
(Auto-Treffer + manuelle Zuordnungen) und schreibt erst nach ausdrücklicher Bestätigung.
Auto-Treffer und manuelle Zuordnungen landen gemeinsam in **einer** SQLite-Transaktion.

## Konsequenzen

- Implementierung einfacher (ein Zustandsautomat statt zwei Modi).
- UX klarer: Nutzer sieht immer erst, was passiert, bevor es passiert.
- dry-run und commit wären redundant gewesen — die Vorschau erfüllt den dry-run-Zweck.
- Abbrechen vor „Jetzt schreiben" hinterlässt DB und Tags unverändert.
