# ADR-0030: Anzeige-Limit der manuellen Zuordnungs-Liste (konfigurierbar, Default 100)

**Status:** Accepted

## Kontext

Im manuellen Zuordnungs-Dialog (`ManualAssignmentDialog`) werden alle passenden QSO-Kandidaten
aus dem in-memory-Suchergebnis in einem Treeview angezeigt. Bei einem leeren oder sehr breiten
Suchfeld (z. B. nur Rufzeichen ohne Datum/Band) können mehrere Hundert oder Tausend Treffer
entstehen. Das Befüllen des Treeviews verlangsamt die GUI spürbar.

**Wichtige Klarstellung:** Der Suchraum (`RunResult.candidates`) liegt vollständig in-memory.
Es findet **kein zusätzlicher DB-Zugriff** für die Suche statt. Das Limit ist eine reine
**Anzeige-Begrenzung** — es spart keinen DB-Roundtrip, sondern schützt nur die GUI-Flüssigkeit.

## Entscheidung

Ein konfigurierbares Anzeige-Limit wird eingeführt:

- **Default:** 100 Einträge.
- **0 = kein Limit** (alle Treffer anzeigen).
- **Einstellbar:** 10 / 100 / 1000 als Schnellwahl, zusätzlich frei eingebbar.
- **Persistenz:** Feld `manual_match_limit: int = 100` in `AppConfig`; wird via
  `save_config` mit Crypto-Backend persistiert (Token-Sicherheitsregeln greifen weiterhin).
- **Einstellungsort:** Setup-Assistent (`SetupWizard`) unter „Einstellungen", editierbare
  Combobox mit Vorschlagswerten.
- **Hinweistext bei Begrenzung:** Dialog zeigt `(zeige N von M)` im LabelFrame-Titel,
  wenn die Anzeige beschnitten wird. Kein Hinweis wenn total ≤ limit.

Implementierung als reine, tk-freie Funktion `apply_display_limit(candidates, limit)` in
`filter_util.py` — vollständig testbar ohne Display.

## Migration

Additiver Default: bestehende Configs ohne das Feld funktionieren weiterhin.
`migrate_config` setzt das Feld auf 100 falls es fehlt. Kein Versions-Bump nötig.

## Konsequenzen

- **Positiv:** GUI bleibt flüssig auch bei breitem Suchfeld; Nutzer kann das Limit
  seinen Gewohnheiten anpassen; kein unnötiger DB-Zugriff (war ohnehin nicht geplant).
- **Negativ:** Bei Default 100 sieht der Nutzer möglicherweise nicht alle Treffer —
  der Hinweis `(zeige N von M)` macht das aber explizit sichtbar.
- **Neutral:** Das Limit hat keinen Einfluss auf die Korrektheit der Zuordnung —
  ein gesuchtes QSO ist immer auffindbar durch Eingabe genauerer Suchfelder.
