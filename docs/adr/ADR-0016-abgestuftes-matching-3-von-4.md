# ADR-0016: Abgestuftes Matching — 3-von-4 mit Widerspruchs-Ausschluss

**Status:** Accepted

## Kontext

Das ursprüngliche Matching-Modell (bis Schritt 4a) erforderte, dass alle vier Felder
(Rufzeichen, Datum, Band, Mode) **positiv übereinstimmen**, um einen Treffer als „sicher"
einzustufen. War auch nur ein Feld `None` (OCR kaputt, nicht normalisierbar), landete die
Karte immer bei „unsicher", selbst wenn die drei übrigen Felder eindeutig identifizierend waren.

Das führte zu unnötig vielen „unsicher"-Einstufungen: In der Praxis ist ein einzelnes
unlesbares Feld (z. B. zerstörtes Band-OCR) häufig, aber drei übereinstimmende Felder
(Call + Datum + Mode) reichen in der Regel aus, das QSO eindeutig zu identifizieren.

Gleichzeitig muss das Modell Falsch-Positive zuverlässig verhindern: Wenn ein lesbares
Kartenfeld einem Kandidaten **widerspricht**, darf dieser Kandidat niemals als „sicher"
gelten — auch nicht, wenn alle anderen Felder passen.

## Entscheidung

**Drei Feldzustände** für jedes Matchfeld:

| Zustand | Bedingung | Wirkung |
|---------|-----------|---------|
| STIMMT ÜBEREIN | Feld lesbar (≠ None) und passt zum Kandidaten | positiv, zählt zur 3-von-4-Schwelle |
| FEHLT / UNBESTIMMT | Feld ist None | neutral — schließt nicht aus, zählt nicht positiv |
| WIDERSPRICHT | Feld lesbar (≠ None), passt **nicht** | schließt diesen Kandidaten aus |

**Eingrenzung:** Kandidaten werden ausgeschlossen, wenn ein lesbares Kartenfeld
widerspricht. Fehlende Felder grenzen nicht ein.

**3-von-4-Schwelle:** Genau 1 Kandidat nach Eingrenzung → „sicher" **nur wenn**:
- mindestens **3 der 4 Felder** positiv übereinstimmen (Rufzeichen + mind. 2 weitere),
- und kein lesbares Feld widerspricht (durch Eingrenzung bereits sichergestellt).

Weniger als 3 positive Felder → „unsicher".

**Rufzeichen ist Pflicht:** Das Rufzeichen ist immer eines der mindestens 3 positiven
Felder; ohne Rufzeichen-Treffer gibt es keinen Kandidaten.

**Band/Mode bleiben exakt** (kein Fuzzy, unabhängig von `fuzzy_enabled`). Fuzzy nur
auf Rufzeichen (ADR-0007, ADR-0010).

**Suffix-Unterschied-Regel** (§6.3) bleibt unverändert und ist strenger als 3-von-4:
Bei unterschiedlichem Zusatz müssen Datum + Band + Mode alle drei explizit übereinstimmen
(kein None erlaubt).

## Konsequenzen

**Positiv:**
- Mehr legitime Treffer bei häufigem OCR-Versagen in einem Einzelfeld (insbesondere Band).
- Falsch-Positiv-Schutz bleibt vollständig erhalten: Widerspruch schließt aus,
  fehlende Felder raten nie einen Wert herbei.
- Eingrenzung via lesbare Felder löst Mehrfachkandidaten auf (z. B. gleiche Station,
  zwei Bänder am selben Tag: Karte nennt ein Band → nur das passende QSO bleibt).

**Beachten:**
- Die 3-von-4-Schwelle ist eine bewusste Balance: 2-von-4 (z. B. nur Call + Datum)
  reicht nicht — zu viele QSOs könnten zufällig passen.
- Wenn ein Feld fehlt und dadurch mehrere Kandidaten entstehen (z. B. Band fehlt,
  DB hat Call+Datum auf 6m und 20m), bleibt das Ergebnis „unsicher" — die Eingrenzung
  wirkt nur bei lesbaren (nicht-None) Feldern.
- Die Suffix-Unterschied-Regel (strenger: alle 3 Nicht-Call-Felder müssen explizit
  matchen) bleibt erhalten, weil dort die Call-Identität bereits unsicher ist.
