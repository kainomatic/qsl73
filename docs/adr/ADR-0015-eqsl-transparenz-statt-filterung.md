# ADR-0015: eQSL/Fremdbestätigungen — Transparenz statt Filterung

**Status:** Accepted

## Kontext

Manche Nutzer scannen nicht nur Papierkarten, sondern gelegentlich auch ausgedruckte
eQSL-/LoTW-Bestätigungen in Paperless ein. Paperless kann zudem automatisch Tags per
KI vergeben, sodass solche Ausdrucke versehentlich den `qsl-card`-Tag erhalten und damit
in QSL73s Verarbeitungswarteschlange landen.

Gleichzeitig sind **Doppelbestätigungen legitim und häufig**: Viele Funkamateure empfangen
für dasselbe QSO sowohl eine eQSL (elektronisch) als auch eine Papierkarte — beide
Bestätigungstypen sind dann korrekt im Log eingetragen. Ein vorhandener EQSL- oder
LOTW-Eintrag in `qsoconfirmations` sagt daher nichts darüber aus, ob die eingescannte
Karte eine echte Papierkarte oder ein Ausdruck ist.

Bisherige Überlegung (verworfen): QSL73 könnte ausgedruckte eQSLs per Bildanalyse erkennen
und aus der Verarbeitung ausschließen (z. B. am Layout, Logo, Schriftbild von eQSL.cc
oder LoTW-Ausdrucken).

## Entscheidung

QSL73 **filtert nicht** und **blockiert nicht** auf Basis vorhandener eQSL/LoTW-Bestätigungen.
Stattdessen:

1. **Vorhandene Bestätigungen als Zusatzinfo:** Beim Matchen eines QSOs werden alle
   Bestätigungstypen mit R="Yes" aus dem `qsoconfirmations`-Feld ausgelesen (EQSL, LOTW,
   QRZCOM usw.), ausgenommen das Papier-QSL-Feld selbst. Diese Information wird als
   Zusatzfeld an das Match-Ergebnis angehängt.

2. **Anzeige in der Vorschau:** Die Vorschau-Liste (§5, §9) zeigt pro Karte/QSO, welche
   Bestätigungstypen bereits vorliegen (z. B. „bereits bestätigt via: EQSL, LOTW"),
   sofern welche vorhanden sind. Der Nutzer kann so vor dem Klick „Jetzt schreiben"
   erkennen, wenn eine Karte möglicherweise ein eQSL-Ausdruck ist.

3. **Keine Einstufungsänderung:** Die Anzeige ändert die Match-Einstufung sicher/unsicher/
   kein Match **nicht**. Ein sonst sicherer Match bleibt sicher. Kein Blockieren, keine
   automatische Herabstufung.

4. **Keine Bildanalyse:** QSL73 unternimmt keinen Versuch, per OCR-Inhalt oder
   Bildmuster-Analyse eQSL-Ausdrucke von echten Papierkarten zu unterscheiden. Das wäre
   unzuverlässig und würde legitime Papierkarten fälschlicherweise sperren können.

5. **Tag-Disziplin als Nutzerpflicht (§8):** QSL73 behandelt alle Dokumente mit dem
   `qsl-card`-Tag als echte Papierkarten. Die Verantwortung für korrekte Verschlagwortung
   liegt beim Nutzer.

## Konsequenzen

- **Nutzer braucht die Vorschau-Info zur Selbstkontrolle:** Wer versehentlich eQSL-Ausdrucke
  mit `qsl-card` getaggt hat, sieht das an der Bestätigungs-Anzeige und kann die Zuordnung
  abbrechen oder den Tag manuell korrigieren.
- **Tag-Disziplin bleibt Nutzerverantwortung:** QSL73 kann den `qsl-card`-Tag nicht selbst
  setzen oder entfernen — das ist Paperless-Konfiguration. Bei automatischer Tag-Vergabe (KI)
  muss der Nutzer prüfen, ob `qsl-card` unbeabsichtigt vergeben wird.
- **Doppelbestätigungen werden nicht behindert:** Ein QSO kann korrekt eQSL + LOTW +
  Papier-QSL bestätigt sein. QSL73 schreibt in diesem Fall die Papier-QSL-Bestätigung
  wie erwartet — die Anzeige der vorhandenen eQSL/LOTW-Einträge ist nur Info.
- **Implementierungsaufwand minimal:** Die Daten liegen ohnehin im `qsoconfirmations`-Feld
  vor (das beim Matchen gelesen wird); es muss nur ausgelesen und weitergegeben werden.
