# ADR-0064: Eingangs-Tag als Arbeitskorb — Entfernen bei Bestätigen/Ignorieren, Alt-Bestand-Aufräumen

**Status:** Accepted

## Kontext

Der Eingangs-Tag (`config.tags.input`, Standardvorschlag `qsl-card`, bei DF1DS „neu")
ist der Tag, über den QSL73 die abzuarbeitenden Karten aus Paperless lädt. Bisher blieb
er nach dem Bestätigen ("Jetzt schreiben") oder Ignorieren (ADR-0059) unverändert am
Dokument bestehen — QSL73 blendet die Karte zwar serverseitig aus (`run_pass` schließt
`confirmed`/`ignored` aus, ADR-0032/ADR-0059), aber in Paperless selbst blieb sie im
Eingangs-Arbeitskorb sichtbar.

DF1DS' Wunsch (Issue #41): Der Eingangs-Tag ist ein **Arbeitskorb**, keine
Dauer-Kategorie — er soll von erledigten Karten verschwinden. Kein neuer Tag, kein
neues Config-Feld für dieses Verhalten selbst (gilt immer, kein Schalter).

Die 11 Grundentscheidungen wurden mit DF1DS im Issue geklärt, bevor dieser Auftrag sie
umsetzt (ADR-0060: erster Umsetzungsauftrag eines vorgemerkten Features → ADR hier).

## Entscheidung

1. **Gilt immer** — kein Schalter, keine Config-Änderung für das Verhalten selbst.
2. **Bestätigen** ("Jetzt schreiben"): tatsächlich geschriebene Karten erhalten den
   Bestätigt-Tag **und** verlieren den Eingangs-Tag, in **einem** PATCH pro Dokument
   (`PaperlessClient.replace_tags_on_document`, neu — Hinzufügen und Entfernen in einem
   Aufruf, kein halber Zustand). Nur **nach** erfolgreicher DB-Transaktion (ADR-0003).
   Tag-Fehler bleiben nicht-fatal (ADR-0031 §5, bestehende `tag_warnings`-Mechanik).
3. **Übersprungene Karten** (`result.skipped`, z. B. R-Feld extern verändert) bekommen
   **weder** den Bestätigt-Tag **noch** die Eingangs-Tag-Entfernung — sie bleiben
   unverändert im Arbeitskorb. `write_selected` schließt sie explizit aus der
   Tag-Schleife aus (vorher liefen `confirmed_doc_ids` ungefiltert durch — mit
   Tag-Entfernen wäre das gefährlich geworden: eine übersprungene Karte hätte sonst
   ihren Arbeitskorb-Platz verloren, obwohl das QSO nicht bestätigt wurde).
4. **Ignorieren** (`ignore.ignore_card`): Ignoriert-Tag dran, Eingangs-Tag weg — ein
   PATCH. **Wieder aufnehmen** (`ignore.unignore_card`): Ignoriert-Tag weg,
   Eingangs-Tag wieder dran — ein PATCH. Ohne die Rückgabe des Eingangs-Tags käme die
   Karte nie mehr in einen Durchlauf zurück. Andere Tags bleiben in beiden Fällen
   unverändert.
5. **Folge für ADR-0059:** Das Fenster „Ignorierte Karten…" und der
   `ignored_count`-Zähler (Statuszeile) suchen nicht mehr nach Eingangs- UND
   Ignoriert-Tag, sondern nur noch nach dem **Ignoriert-Tag** — sonst würden neu
   ignorierte Karten (ohne Eingangs-Tag) nicht mehr gefunden. Alt-Bestand aus v0.5.0
   (der noch beide Tags trägt) wird von einer Ein-Tag-Suche ebenfalls gefunden, bleibt
   also weiterhin sichtbar/zählbar.
6. **Serverseitige Ausschlüsse in `run_pass` bleiben unverändert** (`get_documents_by_tag`
   schließt `confirmed` und `ignored` aus, ADR-0032/ADR-0059) — als Sicherheitsnetz,
   u. a. weil ein Paperless-Retagger den Eingangs-Tag per Auto-Matching erneut anhängen
   kann, unabhängig vom hier beschriebenen Entfernen.
7. **Einmalige Alt-Bestand-Abfrage nach dem Update:** Karten, die von *früheren*
   QSL73-Versionen bestätigt/ignoriert wurden, tragen den Eingangs-Tag noch. Ein
   additives Config-Feld `app.input_tag_cleanup_done` (Default `False`, Muster
   ADR-0055 — kein `config_version`-Bump) merkt, ob die einmalige Abfrage bereits
   erledigt ist. **Neuinstallation** (Setup-Assistent frisch durchlaufen,
   `setup_assistant.create_initial_config`) markiert das Feld sofort als `True` — bei
   einem leeren System gibt es nichts aufzuräumen.
8. **Prüfung im Hintergrund nach Anzeige des Hauptfensters** (Muster
   `schedule_update_check`/ADR-0023-Queue-Polling — kein `self.after(0, …)` direkt aus
   dem Hintergrund-Thread, ADR-0063): `RunController.start_input_tag_cleanup_check`
   zählt Dokumente mit (Eingangs-Tag + Bestätigt-Tag) und (Eingangs-Tag + Ignoriert-Tag)
   und legt ein `InputTagCleanupCheckDoneEvent` in dieselbe Event-Queue wie die übrigen
   Hintergrund-Ergebnisse. Summe 0 → still als erledigt vermerkt, kein Dialog. Summe > 0
   → Dialog erklärt die Verhaltensänderung, nennt die Anzahl, fragt „Jetzt entfernen?"
   (Ja/Später/Nicht mehr fragen). **Paperless nicht erreichbar oder Fehler → NICHT als
   erledigt vermerkt**, kein Fehlerdialog beim automatischen Start-Check (nächster Start
   versucht erneut) — ein unerreichbarer Server darf nicht als „nichts zu tun"
   interpretiert werden. Der Start wird nie blockiert (Delay vor dem Check, analog
   Update-Prüfung, leicht versetzt damit beide Hintergrund-Prüfungen nicht exakt
   gleichzeitig starten).
9. **Dauerhafter Menüpunkt** „Bearbeiten → Eingangs-Tag bei erledigten Karten
   entfernen…" mit derselben Zähl-/Rückfrage-/Ausführ-Logik (`manual=True`), jederzeit
   nutzbar — deckt den „Später"-Fall ab und den Fall, dass ein Retagger den Eingangs-Tag
   erneut anhängt. Bei `manual=True` und Anzahl 0 erscheint ein Info-Dialog statt
   stillem Vermerken.
10. **Ausführung** (`input_tag_cleanup.remove_input_tag_from_leftovers`): entfernt
    **ausschließlich** den Eingangs-Tag, alle anderen Tags bleiben unverändert — über
    die bestehende, getestete `PaperlessClient.remove_tag_from_document` (kein neues
    Tag wird gleichzeitig gesetzt, also genügt hier die einfache Entfernen-Methode statt
    `replace_tags_on_document`). **Einzel-PATCH pro Dokument statt
    `/api/documents/bulk_edit/`:** die erwartete Alt-Bestand-Menge ist klein
    (einstellig bis niedrig zweistellig pro Nutzer), Einzel-PATCH gibt triviale
    Fehlerisolation pro Dokument (Issue-Vorgabe: „Fehler einzelner Dokumente brechen den
    Rest nicht ab") und nutzt eine bereits getestete, etablierte Methode — ein neuer
    Bulk-Client-Aufruf hätte dafür ohne klaren Nutzen zusätzliche API-Fläche und eigene
    Tests gebraucht. Fehler einzelner Dokumente werden geloggt und gezählt, brechen den
    Rest nicht ab; danach **ein** Sammel-Audit-Eintrag (`CleanupAuditEntry`,
    `aktion=eingangs_tag_aufraeumen | entfernt=N | fehler=M`) statt eines Eintrags pro
    Dokument.
11. **NICHT automatisch/still aufräumen** — weder beim Update noch im Durchlauf
    (`run_pass` bleibt rein lesend, KONZEPT §5). Immer nur nach ausdrücklicher
    Rückfrage (Dialog oder Menüpunkt).
12. **Beta/Stable getrennte Configs:** Da `input_tag_cleanup_done` pro Config-Datei
    gespeichert wird, fragen Beta und Stable unabhängig — die zweite findet in der
    Regel 0 (derselbe Alt-Bestand wurde beim ersten Kanal bereits aufgeräumt) und bleibt
    still. Kein Sonderfall nötig.

## Konsequenzen

**Positiv:**
- Paperless-Eingangskorb bleibt nach Bestätigen/Ignorieren tatsächlich leer — deckt
  sich mit der Nutzererwartung "Arbeitskorb, kein Dauer-Status".
- Kein halber Zustand: Tag-Setzen und -Entfernen laufen je Aktion in genau einem PATCH.
- Alt-Bestand wird nicht still verändert — Nutzer entscheidet aktiv, mit klarer
  Fehlerbehandlung bei nicht erreichbarem Paperless.

**Negativ / Einschränkungen:**
- Nutzer, die den Eingangs-Tag zusätzlich als eigene Dauer-Kategorie/-Filter in
  Paperless genutzt haben, sind von der Verhaltensänderung betroffen (README-Hinweis,
  CHANGELOG prominent unter „Changed").
- Zwei zusätzliche Paperless-Requests pro Alt-Bestand-Zählung
  (`count_documents_with_all_tags` je einmal für Bestätigt- und Ignoriert-Kombination) —
  vernachlässigbar, läuft nur einmalig bzw. auf manuellen Wunsch.
- `write_selected` und `ignore.py` verlieren die direkten `add_tag_to_document`/
  `remove_tag_from_document`-Aufrufe zugunsten von `replace_tags_on_document` — bestehende
  Tests wurden entsprechend umgestellt (kein Verhaltensbruch, nur andere Client-Methode).

## Bezug zu bestehenden ADRs

- **ADR-0003** (Schreibreihenfolge DB→Tags): unverändert — der Bestätigt-Tag/
  Eingangs-Tag-Wechsel läuft weiterhin ausschließlich nach erfolgreicher DB-Transaktion.
- **ADR-0031 §5** (kein automatisches Tag-Anlegen, Tag-Fehler beim Schreiben nicht
  fatal): unverändert — `replace_tags_on_document` legt keine Tags an, fehlende
  Add-Tags werfen wie bisher `PaperlessNotFoundError`, im Schreibpfad nicht-fatal
  abgefangen.
- **ADR-0059** (Ignorieren ersetzt Unsicher-Tag): Grundentscheidungen 1–6 dort bleiben
  unverändert; Entscheidung 5 hier ändert ausschließlich die Tag-Suchlogik von
  `ignored_window`/`ignored_count` — als Nachtrag dort vermerkt, ADR-0059 selbst wird
  nicht umgeschrieben.
- **ADR-0055** (additive Config-Migration ohne Versions-Bump): Muster für
  `app.input_tag_cleanup_done` übernommen.
- **ADR-0023/ADR-0063** (Queue-Polling statt cross-thread `self.after`): Muster für
  die Hintergrund-Alt-Bestand-Prüfung/-Ausführung übernommen — neue Event-Typen
  `InputTagCleanupCheckDoneEvent`/`InputTagCleanupRunDoneEvent` laufen über dieselbe
  Event-Queue/`_poll()`-Mechanik wie alle übrigen Hintergrund-Ergebnisse.
- **KONZEPT §5** (Durchlauf bleibt rein lesend): Grundentscheidung 11 hier hält daran
  fest — kein automatisches/stilles Schreiben, weder im Durchlauf noch beim Update.
