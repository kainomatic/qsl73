# ADR-0065: Beta-Vorschlag nach Issue-Abschluss; Stable-Release nur auf ausdrückliche DF1DS-Ansage

**Status:** Accepted

## Kontext

ADR-0046 legt den technischen Beta→Stable-Workflow fest (Versionsnummer,
CHANGELOG-Einfrieren, Auslöser-Rollen). ADR-0048 regelt den Sonderfall
Stable-Hotfix. Offen war bislang das **Arbeitsvorgehen**: Wann wird nach
Abschluss eines Issues eine Beta geschnitten, und unter welchen Bedingungen
darf daraus ein Stable-Release werden?

Anlass: Nach Abschluss von Issue #41 (Commit `2eddd81` auf `dev`) sollte die
erste Beta der kommenden MINOR v0.6.0 geschnitten werden — ausdrücklich ohne
jeden `main`-Eingriff. Diese Abgrenzung war bisher nicht als Regel
festgehalten, nur implizit aus ADR-0046 §5 ableitbar.

## Entscheidung

1. **Nach Abschluss eines Issues KANN eine Beta vorgeschlagen bzw. geschnitten
   werden.** Ein Beta-Tag aus `dev` (`vX.Y.Z-betaN`) ist risikoarm — er ist
   für Stable-Nutzer unsichtbar (Pre-Release, ADR-0045 filtert nach Kanal) und
   erfordert keinen Eingriff auf `main`. ADR-0046 §5 erlaubt Claude Code
   bereits, einen solchen Tag auf ausdrücklichen Auftrag zu setzen und zu
   pushen — diese ADR bekräftigt das als Standard-Arbeitsschritt nach
   Issue-Abschluss, nicht nur als Einzelfall-Erlaubnis.
2. **Ein Stable-Release (`dev→main`-Merge + Stable-Tag) wird NIE automatisch
   oder als selbstverständliche Folge einer Beta gemacht.** Es erfolgt
   ausschließlich auf ausdrückliche Ansage von DF1DS, nach Desktop-Review
   (bekräftigt ADR-0046 §5 und ADR-0048). Weder ein grüner Beta-Build noch
   ein abgeschlossenes Issue sind für sich genommen ein Auslöser.
3. **Abgrenzung Beta vs. Stable:**
   - Beta: risikoarm, Pre-Release, für Stable-Nutzer unsichtbar, kein
     `main`-Eingriff — darf Claude Code auf Auftrag auslösen.
   - Stable: öffentlich sichtbar, bewusste Entscheidung — ausschließlich
     DF1DS, nie als impliziter Folgeschritt einer Beta.

## Konsequenzen

- Ein CC-Auftrag „Beta schneiden" darf ohne separate Rückfrage zum
  `main`-Eingriff ausgeführt werden — solange er sich (wie hier) ausdrücklich
  auf den Beta-Tag aus `dev` beschränkt.
- Ein Stable-Release-Auftrag muss die DF1DS-Entscheidung explizit benennen;
  Claude Code leitet daraus nie von sich aus einen Stable-Schritt ab, auch
  wenn eine vorherige Beta erfolgreich war.
- Bezug: ADR-0046 (technischer Ablauf), ADR-0048 (Stable-Hotfix-Sonderfall),
  ADR-0060 (ADR-Zeitpunkt bei vorgemerkten Features — hier: Entscheidung wirkt
  über das konkrete Feature hinaus, daher sofortiges ADR statt Issue-Notiz).
