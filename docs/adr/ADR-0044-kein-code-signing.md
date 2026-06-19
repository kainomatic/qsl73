# ADR-0044: Kein Code-Signing — SmartScreen-Warnung dokumentiert statt Zertifikat

**Status:** Accepted

## Kontext

Windows SmartScreen prüft beim Ausführen heruntergeladener .exe-Dateien, ob der
Herausgeber bekannt ist (Zertifikat + Reputations-Aufbau über Download-Volumen).
Der QSL73-Installer ist nicht code-signiert. Folge: beim ersten Ausführen erscheint die
Meldung „Der Computer wurde durch Windows geschützt — Unbekannter Herausgeber". Nutzer
müssen aktiv „Weitere Informationen → Trotzdem ausführen" wählen; andernfalls wird der
Installer abgebrochen.

## Optionen

| Option | Kosten | Wirkung |
|--------|--------|---------|
| **(a) Standard-OV-Zertifikat** | ca. 100–300 €/Jahr | Warnung bleibt zunächst, verschwindet erst nach ausreichend vielen Downloads (Reputations-Aufbau durch SmartScreen) |
| **(b) EV-Zertifikat** | ca. 300–500 €/Jahr + Hardware-Token | Umgeht SmartScreen sofort; erfordert Hardware-Token und aufwändigere CI-Integration |
| **(c) Kein Zertifikat, Warnung dokumentieren** | 0 € | Nutzer sehen die Warnung und bestätigen einmalig „Trotzdem ausführen" |

## Entscheidung

Option **(c)** — kein Code-Signing-Zertifikat.

**Begründung:**
- QSL73 ist ein GPLv3-Amateurfunk-Hobbyprojekt mit einem einzelnen Entwickler und einer
  technikaffinen Zielgruppe; die jährlichen Zertifikatskosten stehen in keinem sinnvollen
  Verhältnis zum Nutzen.
- Der gesamte Quellcode ist auf GitHub öffentlich einsehbar; Nutzer können die Herkunft
  der Software selbst nachvollziehen.
- Die SmartScreen-Warnung ist einmalig (beim ersten Ausführen des Installers) und lässt
  sich mit zwei Klicks übergehen.
- README.md enthält einen sachlichen Hinweis mit der Schritt-für-Schritt-Anleitung
  („Weitere Informationen" → „Trotzdem ausführen"), der die Warnung entmystifiziert.

**Neubewertung:** Falls das Projekt künftig breiter verteilt wird oder Nutzerrückmeldungen
zeigen, dass die Warnung ein echtes Hindernis darstellt, kann ein OV-Zertifikat
nachgerüstet werden (kein Eingriff in Release-Workflow nötig, nur Signing-Schritt ergänzen).

## Konsequenzen

- Nutzer sehen beim ersten Ausführen des Installers die SmartScreen-Warnung und müssen
  „Weitere Informationen → Trotzdem ausführen" klicken. Dies gilt für Stable und Beta.
- Kein laufender Kostenaufwand für Zertifikat oder Token-Verwaltung.
- Der README-Hinweis (Abschnitt „Installation (Nutzer)") beschreibt das Vorgehen.
- Zukünftige Neubewertung möglich ohne ADR-Änderung (Zertifikat = reine Build-Ergänzung).
