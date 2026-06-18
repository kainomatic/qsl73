# ADR-0034: main-Branch-Aktualisierung ohne Release

**Status:** Accepted

## Kontext

Der `main`-Branch enthielt nach Schritt 1 (Repo-Grundgerüst) keine weiteren Commits mehr —
die gesamte Entwicklung (Schritte 2–7b-1, 95 Commits) lief ausschließlich auf `dev`.
Da GitHub `main` als Default-Branch anzeigt, sahen Besucher des öffentlichen Repos einen
veralteten Stand mit einer MIT-Lizenz (inzwischen auf GPLv3 gewechselt, ADR-0018).

## Entscheidung

`main` wurde einmalig per Fast-Forward auf den aktuellen `dev`-Stand gebracht
(`git merge --ff-only dev`), um den öffentlich sichtbaren Default-Branch zu aktualisieren.

**Grundsatz:** `main` darf jederzeit per Fast-Forward von `dev` aktualisiert werden, wenn
der öffentlich sichtbare Stand aktuell gehalten werden soll — das ist **kein Release**.
Ein Release entsteht ausschließlich durch einen getaggten GitHub-Release (Schritt 9,
ADR-0021). `main`-Push ≠ Release.

- Kein Tag erstellt.
- Kein GitHub-Release angelegt.
- Keine Versionsänderung.

Der Beta-/Stable-Update-Mechanismus (ADR-0021) prüft ausschließlich gegen getaggte
Releases — ein reiner `main`-Push löst kein Nutzer-Update aus.

## Konsequenzen

**Positiv:**
- `main` zeigt jetzt die korrekte GPLv3-Lizenz und den aktuellen Entwicklungsstand.
- Repo-Besucher sehen den vollständigen, konsistenten Codestand.
- Das Muster „Fast-Forward main von dev = kein Release" ist explizit dokumentiert und
  kann künftig reproduziert werden, ohne jedes Mal abwägen zu müssen.

**Negativ / Risiken:**
- `main` enthält nun unveröffentlichten Entwicklungsstand (kein getestetes Release).
  Das ist bewusst akzeptiert, da kein Installer/Bundle existiert und Nutzer den Code
  aktuell nur über den Quellcode nutzen.
- Fast-Forward funktioniert nur, wenn `main` keine eigenen Commits hat (ist immer
  der Fall solange nur Claude Code auf `dev` entwickelt und `main` ausschließlich
  über dieses Verfahren aktualisiert wird).
