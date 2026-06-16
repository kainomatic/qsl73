# ADR-0001: 3-Rollen-Arbeitsmodell

**Status:** Accepted

## Kontext

Claude Desktop hat auf dem Entwicklungsrechner nur lesenden Dateisystem-Zugriff und kann
nicht selbst committen. Der User DF1DS vermittelt zwischen den beiden Claude-Instanzen.
Es braucht eine klare Rollentrennung, damit Verantwortlichkeiten und der Repo-Pfad
(C:\Entwicklung\qsl73) eindeutig sind.

## Entscheidung

- **Claude Desktop** = Architekt & Reviewer. Liest Repo read-only, schreibt KONZEPT.md und
  Prompts, prüft jeden Schritt gegen die Akzeptanzkriterien. Commitet nie direkt.
- **DF1DS** = Vermittler. Überträgt Prompts und Repo-Stände zwischen Desktop und Code.
- **Claude Code** = alleiniger ausführender Maintainer. Baut, testet, committet, pflegt
  GitHub/Releases/Doku.

## Konsequenzen

- Alle Code- und Doku-Änderungen laufen ausschließlich über Claude Code.
- Das Repo muss unter `C:\Entwicklung\` liegen, damit Desktop lesend reviewen kann.
- Jeder Schritt endet mit einer Rückmeldung an Desktop; erst nach Review-Freigabe
  beginnt der nächste Schritt.
