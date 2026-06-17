# ADR-0018: Lizenzwechsel von MIT auf GPLv3

**Status:** Accepted

## Kontext

QSL73 greift schreibend in die Log4OM-SQLite-Datenbank des Nutzers ein. Ein Tool, das
fremde Logbuch-Daten verändert, sollte in jeder verbreiteten Version für den Nutzer
prüfbar sein — auch wenn es jemand anderes weiterentwickelt oder verbreitet.

Unter MIT kann jede Person das Projekt forken, die Quellen schließen und eine proprietäre
Variante verkaufen, ohne den Quellcode offenzulegen. Das widerspricht dem Transparenz-
Prinzip von QSL73 (KONZEPT.md §1) und dem Vertrauen, das Nutzer in ein schreibendes
Tool setzen müssen.

DF1DS ist der einzige Autor aller Commits — ein Lizenzwechsel ist daher ohne Zustimmung
Dritter möglich.

## Entscheidung

Lizenzwechsel von **MIT** auf **GNU General Public License Version 3 (GPLv3)**.

- Alle existierenden Quelldateien erhalten einen SPDX-Header:
  `SPDX-License-Identifier: GPL-3.0-or-later`
- Die `LICENSE`-Datei enthält den unveränderten offiziellen GPLv3-Text (bezogen von
  gnu.org) sowie den Copyright-Hinweis: `Copyright (C) 2026 DF1DS (kainomatic)`.

**Warum GPLv3 und nicht LGPL oder AGPL?**
- LGPL: erlaubt proprietäre Einbettung als Bibliothek — unerwünscht; QSL73 ist ein
  eigenständiges Endnutzer-Programm, kein Framework.
- AGPLv3: würde auch Netzwerknutzung erfassen; irrelevant für ein lokales Desktop-Tool.
- GPLv3: exakt das richtige Niveau — Copyleft für Distributionen und Weiterentwicklungen,
  ohne das Nutzungsrecht des Einzelnutzers einzuschränken.

## Konsequenzen

**Positiv:**
- Weiterentwicklungen, die verbreitet werden, müssen den Quellcode offenlegen.
- Das schreibende Tool bleibt in allen kursierenden Varianten prüfbar.
- Copyleft-Signal: das Projekt ist offen und will es bleiben.

**Zu beachten:**
- Einige kommerzielle Nutzungsszenarien (proprietäre Integration) werden eingeschränkt;
  für ein Amateurfunk-Hobbytools ohne kommerzielle Absicht unproblematisch.
- Abhängigkeiten (rapidfuzz, requests, pyzbar u. a.) sind MIT/Apache-2.0/LGPL-lizenziert
  und GPLv3-kompatibel — keine Lizenzkonflikt-Probleme bekannt.
