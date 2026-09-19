# ADR-0066: Bestätigungsübersicht — read-only-Datenmodell und Fakten-vs-Merker-Trennung

**Status:** Accepted

## Kontext

Issue #42 („Werkzeug Bestätigungsübersicht") verlangt ein neues, von Log4OM unabhängiges
Fenster, das den Bestätigungsstatus aller QSOs über alle Dienste (QSL/Papier, LoTW, eQSL,
QRZ, ClubLog, HRDLog, HamQTH) übersichtlich zeigt. Das Issue hält bereits acht
Grundentscheidungen fest (ADR-0060-Regel: ADR folgt mit dem ersten Umsetzungsauftrag).
Dieser Auftrag (1 von 2) baut das tk-freie Logikmodul `src/qsl73/confirmations.py`
(Laden, Normalisieren, Kennzahlen, Filter) — das Fenster folgt in Auftrag 2.

Der Handtest vom 2026-09-19 (`docs/discovery.md` §7.1) hat die exakten Log4OM-Strings für
`Requested`/`Queued`/`Invalid` gesichert und einen wichtigen Nebenbefund geliefert: Bei
`Requested`/`Queued` entfernt Log4OM die Felder `SV`/`RV` aus dem QSL-Block.

## Entscheidung

**1. Strikt read-only (Issue-Grundentscheidung 2).** Die DB wird ausschließlich über eine
SQLite-URI-Verbindung mit `mode=ro` geöffnet (`open_readonly_connection`) — kein Backup,
keine Transaktion, kein Schreibpfad. Der bestehende `validate_schema`-Check aus
`log4om_db.py` wird wiederverwendet (nicht dupliziert); bei Schema-Abweichung liefert
`load_confirmation_data` einen sauberen `SchemaError` statt eines Absturzes. Damit ist das
Werkzeug gefahrlos neben einem laufenden Log4OM nutzbar.

**2. Fakten-vs-Merker-Trennung (Issue-Grundentscheidung 3) als zentrales Datenmodell.**
`confirmation_state(status, group)` leitet den Hauptzustand ausschließlich aus harten
Fakten ab (`R="Yes"` > `S="Yes"` > keins) und gibt einen `ConfirmationState`
(NONE/SENT/RECEIVED/INVALID) zurück — bewusst kein Anzeige-Emoji, das ist Sache des
Fensters (Auftrag 2). `has_marker(status)` prüft unabhängig davon, ob auf Sende- oder
Empfangsseite ein Absichtsmerker (`Requested`/`Queued`) steht, und bei allen Diensten
gleich — ohne die Bedeutung zu deuten (automatischer Standardwert vs. bewusste Anforderung
vs. Druck-Vormerkung bleibt offen, siehe discovery.md §7).

**3. `Invalid` als eigener Zustand (Issue-Grundentscheidung 4).**
`ConfirmationState.INVALID` ist von `NONE` getrennt gehalten: Ein auf `Invalid` gesetzter
Dienst erscheint dadurch nie als „offen" (NONE) und nie als „bestätigt" (SENT/RECEIVED) —
weder im Hauptzustand noch in `compute_metrics` (die nur `S=="Yes"`/`R=="Yes"` zählt).

**4. Zwei Dienstgruppen (Issue-Grundentscheidung 5).** `service_group(ct)` ordnet
Bestätigungsdienste (`QSL`, `LOTW`, `EQSL`, `QRZCOM` — S **und** R relevant) von
Upload-Diensten (`CLUBLOG`, `HRDLOG`, `HAMQTH` — nur S relevant) ab. `confirmation_state`
wertet für Upload-Dienste `R` konsequent nicht aus.

**5. Unbekannte CT-/S-/R-Werte wörtlich durchreichen (Issue-Grundentscheidung 6).**
`service_group` liefert für unbekannte CT-Typen `ServiceGroup.UNKNOWN` statt sie zu
verwerfen; `confirmation_state` behandelt UNKNOWN wie einen Bestätigungsdienst (S und R
auswerten), da die Struktur unbekannter künftiger Diensttypen nicht vorab feststeht.
Unbekannte S-/R-Werte werden 1:1 in `ServiceStatus.s`/`.r` übernommen, nie normalisiert
oder verworfen.

**6. `EXT` nie übernommen (Issue-Grundentscheidung 7).** `ServiceStatus` hat bewusst kein
`ext`-Feld; `parse_qsoconfirmations` liest nur `CT`/`S`/`R`/`SV`/`RV`/`SD`/`RD`.

**7. Fehlende Felder sind normal (discovery.md §7.1 Zusatzbefund 1).** Alle Felder außer
`CT` sind in `ServiceStatus` optional (`None`-Default). Fehlt ein Dienst im
`qsoconfirmations`-Array komplett (wie in den Handtest-Datensätzen, die nur einen
Ein-Eintrag-Block statt der üblichen sieben tragen), ist er schlicht nicht im
`services`-Dict des QSO — kein Sonderfall, keine Annahme über fehlende Dienste.

**8. Robustheit beim Parsen (ADR-0012-Geist).** Leeres/fehlendes/defektes JSON in
`qsoconfirmations` führt nie zum Absturz: `parse_qsoconfirmations` liefert ein leeres
Mapping plus Klartext-Fehlerbeschreibung; das QSO bleibt trotzdem in der geladenen Liste
(`QsoConfirmationRow.confirmations_error`). Einzelne kaputte Einträge innerhalb eines
sonst gültigen Arrays werden übersprungen statt das gesamte Parsen scheitern zu lassen.

## Konsequenzen

**Positiv:**
- Das Fenster (Auftrag 2) kann komplett auf einem stabilen, tk-freien, voll
  unit-getesteten Datenmodell aufsetzen — keine Interpretation der Merker-Bedeutung ist im
  Datenmodell versteckt, sie bleibt wörtlich sichtbar.
- Read-only-Zugriff schließt jedes Schreibrisiko für dieses Werkzeug kategorisch aus.
- Erweiterbarkeit für Stufe 2/3 (Schnellansichten, erweiterte Filter, Aggregation) ist
  vorbereitet: `LOG_COLUMNS` ist um weitere Spalten ergänzbar, `ConfirmationFilters` um
  weitere Felder.

**Negativ / Risiken:**
- Der Upload-Fall (welche Felder sich beim tatsächlichen Hochladen zu einem Dienst ändern,
  ob `SD` gesetzt wird) ist laut discovery.md §7.1 weiterhin nicht per Handtest gesichert —
  bei Bedarf muss das Modul dafür später angepasst werden.
- `ServiceGroup.UNKNOWN` wird wie ein Bestätigungsdienst behandelt (S und R ausgewertet);
  sollte ein künftiger unbekannter Diensttyp strukturell eher einem Upload-Dienst ähneln,
  müsste diese Annahme revidiert werden.

## Bezug

- Issue #42 (Grundentscheidungen 2–7)
- `docs/discovery.md` §2, §3, §7, §7.1
- ADR-0012 (Robustheit — Geist auf Datenparsing übertragen)
- ADR-0004 (Schema-Validierung, hier wiederverwendet statt dupliziert)
