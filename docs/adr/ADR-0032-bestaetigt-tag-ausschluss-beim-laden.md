# ADR-0032: Bereits bestätigte Karten serverseitig ausfiltern (Tag-Ausschluss beim Laden)

**Status:** Accepted

## Kontext

Nach Einführung der Tag-Schreibfunktion (ADR-0031) zeigte sich beim zweiten Durchlauf
ein Workflow-Problem: `get_documents_by_tag` lädt alle Dokumente mit dem Eingangs-Tag
(z. B. "qsl-card"), ohne Rücksicht darauf, ob diese Karten bereits den Bestätigt-Tag
tragen. Ergebnis: Bereits bestätigte Karten erscheinen erneut in der GUI. Weil ihr QSO
inzwischen R="Yes" hat (kein Kandidat mehr), wird die Karte als „Kein Treffer" angezeigt
— irreführend für den Nutzer.

## Entscheidung

`get_documents_by_tag(tag_name, exclude_tag_name=None)` erhält einen optionalen
Ausschluss-Parameter. Wenn `exclude_tag_name` gesetzt ist:

1. `get_tag_id(exclude_tag_name)` wird aufgerufen, um die Paperless-Tag-ID zu ermitteln.
2. Existiert die ID: Die Query wird um `&tags__id__none={id}` ergänzt — Paperless filtert
   serverseitig aus, d. h. Dokumente, die BEIDE Tags tragen (Eingangs- UND Bestätigt-Tag),
   werden gar nicht erst zurückgeliefert.
3. Existiert der Ausschluss-Tag nicht in Paperless (get_tag_id → None): kein Ausschluss,
   alle Dokumente werden wie bisher geladen. Kein Fehler.

`run_pass` übergibt immer `exclude_tag_name=config.tags.confirmed`, sodass bereits
bestätigte Karten im zweiten Durchlauf nicht mehr erscheinen.

Bewusste Nicht-Behandlung: Karten mit R="Yes" aber OHNE den Bestätigt-Tag werden
weiterhin geladen und können als „Kein Treffer" erscheinen. Diese Konstellation
(DB bestätigt, aber Tag fehlt) ist ein Datenproblem des Nutzers und NICHT Teil
dieses Auftrags — der Tag-Filter genügt für den Normalfall.

## Konsequenzen

**Positiv:**
- Bereits bestätigte Karten erscheinen im zweiten Durchlauf nicht mehr als „Kein Treffer"
- Serverseitige Filterung reduziert unnötig transferierte Daten
- Abwärtskompatibel: `get_documents_by_tag(tag_name)` ohne Ausschluss verhält sich unverändert
- Robustheit: fehlendem Ausschluss-Tag führt zu keinem Fehler

**Negativ:**
- Ein zusätzlicher API-Call (GET /api/tags/) pro Lauf für den Tag-ID-Lookup
- Paperless-Filter `tags__id__none` ist nicht Teil der offiziellen Dokumentation;
  funktioniert empirisch korrekt (Django ORM-Negation)
