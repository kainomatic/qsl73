# ADR-0031: Tag-Verwaltung im Setup — Auslesen, Auswählen, Anlegen, Verbindungstest, Schutz vor Auto-Matching, sichtbare Tag-Warnung beim Schreiben

**Status:** Accepted

## Kontext

Beim Schreiben setzt QSL73 Bestätigungs-Tags via `add_tag_to_document`. Existiert der Tag
in Paperless nicht, wirft `get_tag_id` None → `PaperlessNotFoundError` → wurde in
`write_selected` nur geloggt und verschluckt. Der Nutzer bekam kein Feedback.

Zudem waren die drei Tag-Felder im Setup-Assistenten Freitext-Einträge: Tippfehler waren
leicht möglich, und keine Verbindung zu Paperless prüfte die Eingaben.

Ein weiteres Risiko: Paperless-Tags können mit `matching_algorithm != 0` automatisch
Dokumenten zugewiesen werden. Wenn ein Schreib-Tag (confirmed/uncertain) Auto-Matching
aktiviert hat, würde Paperless Karten selbstständig als „bestätigt" markieren — unabhängig
vom QSL73-Schreibvorgang.

## Entscheidung

1. **Tag-Auswahl aus Paperless**: Die drei Tag-Felder werden von Freitext-Entries auf
   Dropdowns umgestellt, befüllt durch `list_tags()` nach erfolgreichem Verbindungstest.

2. **Verbindungstest im Wizard**: Ein „Verbindung testen"-Button prüft URL + Zugangsdaten
   (Token oder User/PW) und zeigt Ergebnis + Tag-Anzahl an. Erst nach erfolgreichem Test
   sind Dropdowns und „Anlegen"-Buttons aktiv.

3. **Tag anlegen mit freiem Namen**: Pro Tag-Feld gibt es ein Eingabefeld + „Anlegen"-Button.
   `create_tag(name, matching_algorithm=0)` legt den Tag ohne Auto-Matching an. Duplikat-Schutz
   via case-insensitivem `get_tag_id`-Check vor dem POST.

4. **Auto-Matching-Warnung**: Wird ein Schreib-Tag (confirmed/uncertain) ausgewählt, dessen
   `matching_algorithm != 0` ist, erscheint eine sichtbare Warnung im Wizard. Der Eingangs-Tag
   (input) ist ausgenommen — für ihn ist Matching unbedenklich. Da Paperless-Tags kein
   Notizfeld haben, ist dieser Hinweis im Wizard der einzige dokumentierte Ort.

5. **Sichtbare Tag-Warnung beim Schreiben**: `write_selected` gibt nun
   `tuple[WriteResult, list[str]]` zurück. Fehlende Tags beim Schreiben führen zu einer
   Warnung im Abschluss-Dialog und in der Statuszeile — kein stilles Verschlucken mehr.
   DB-Schreiben bleibt erfolgreich (ADR-0003 gewahrt). Kein automatisches Tag-Anlegen zur
   Schreibzeit — nur warnen.

6. **matching_algorithm=0 immer bei create_tag**: Default ist `0` (None/kein Auto-Matching).
   Schreib-Tags dürfen NIE von Paperless automatisch vergeben werden, da sonst QSOs ohne
   QSL73-Bestätigung fälschlich als bestätigt markiert werden könnten.

## Konsequenzen

**Positiv:**
- Tippfehler in Tag-Namen ausgeschlossen (Dropdown aus realen Paperless-Tags)
- Frühzeitige Rückmeldung bei falschem Token oder falscher URL
- Schutz vor unbeabsichtigter automatischer Tag-Zuweisung durch Paperless
- Fehlende Tags beim Schreiben werden jetzt sichtbar gemeldet

**Negativ:**
- Wizard erfordert nun eine aktive Verbindung für vollständige Tag-Konfiguration
- Beim Öffnen des Wizards ohne Verbindung sind die Tag-Dropdowns zunächst deaktiviert
  (Nutzer muss erst „Verbindung testen" klicken)
