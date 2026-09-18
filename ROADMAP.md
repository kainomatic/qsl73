# QSL73 – ROADMAP

> Liefert **nur**, was keine andere Quelle liefert: aktueller Stand + priorisierte
> nächste Schritte. Offene Issues → GitHub (einzige Quelle). Änderungs-Details →
> CHANGELOG.md. Begründungen → docs/adr/. Rollen/Arbeitsablauf → CLAUDE.md.
> Wird **überschrieben**, nicht fortgeschrieben (kein neuer Absatz je Änderung).
> → ADR-0061

---

## A) Aktueller Stand

**v0.5.0 STABLE veröffentlicht (2026-09-18).** `main` und `dev` stehen auf demselben
Commit (`749eb2f`, Tag `v0.5.0`) — seit dem ADR-0046-Nachtrag wird `main` nach jedem
Stable-Release per Fast-Forward nach `dev` zurückgemergt; `dev` läuft seither wie
üblich mit weiteren (bislang rein dokumentarischen) Commits voraus, das ist normal.

Keine laufende Beta. Kein aktiver Bau-Auftrag.

Es wird auf keinen bestimmten Praxistest gewartet — nächster Schritt ist einer der
in Abschnitt B priorisierten Punkte.

---

## B) Nächste Schritte

Priorisierte Reihenfolge (DF1DS kann jederzeit umsortieren). Jede Nummer ist ein
GitHub-Issue.

1. **#40** — Testsuite-Stabilität (Tcl-Cross-Thread-Absturz bei vollem Einzelprozess-
   Lauf). Voraussetzung für einen verlässlichen DoD-Nachweis (voller pytest-Lauf) bei
   allen Folgeaufträgen.
2. **#41** — Eingangs-Tag nach Bestätigen/Ignorieren entfernen. Fertig spezifiziert,
   MINOR-Kandidat.
3. **#35** / **#36** — Rufzeichen-Erkennung (Sonderrufzeichen zwei Ziffern; OCR O/0,
   I/1). Entscheidung DF1DS zum Falsch-Positiv-Risiko noch offen, erst ADR-Klärung.
4. **#42** — Werkzeug Bestätigungsübersicht. Grundentscheidungen bereits im Issue
   festgehalten (ADR-0060); Handtest DF1DS zu den exakten Log4OM-Strings noch
   ausstehend.
5. **#38** — Hauptfenster-Zeilen-Tooltip. Komfort-Feature, braucht Tooltip-Infrastruktur-
   Neubau (bestehende Infrastruktur bindet nur pro Widget, nicht pro Treeview-Zeile).
6. **#32** — Schutz gegen Direkt-Commits auf `main`. Prozess-/Doku-Thema, keine
   funktionale Abhängigkeit zu den übrigen Punkten.

**V2** (bewusst zurückgestellt): #25 (Mehrsprachigkeit i18n), #43 (visueller
Blinken-Effekt bei Klick ins gesperrte Fenster).

**Alle offenen Issues (einzige Quelle):**
https://github.com/kainomatic/qsl73/issues — diese Liste hier nennt nur die
Reihenfolge, nicht den vollständigen Bestand.

---

## C) Historie Bauphase

Schritte 0–9 der ursprünglichen Bauphase (bis zum ersten Release v0.1.0). Details,
Testzahlen und die vollständige Schritt-für-Schritt-Fassung: Git-Historie, Commit
`11d1860` (`git show 11d1860:ROADMAP.md`) — letzter Stand vor dieser Umstellung
(ADR-0061). Release-/Beta-/Hotfix-Verlauf danach → CHANGELOG.md.

| Schritt | Ergebnis | Maßgebliche ADRs |
|---|---|---|
| 0 — Discovery | Log4OM-Schreibformat + Paperless-Karten empirisch geklärt (`docs/discovery.md`) | – |
| 1 — Repo-Grundgerüst | Struktur, Branches, `.gitignore`, Lizenz | ADR-0018 |
| 2 — Config & Setup | Config-Load/Save, DPAPI-Token, pytest+CI-Gerüst | – |
| 3 — Paperless-Client | Auth, Dokumente/OCR/Bild/Tag-PATCH gegen Mocks getestet | – |
| 4 — Matching + QR | 3-von-4-Matching mit Widerspruchs-Ausschluss, client-seitiges QR-Decoding | ADR-0007, ADR-0011, ADR-0013–0017 |
| 5 — Schreiblogik | Transaktion, WAL, Vor-Backup, Nebenläufigkeits-Schutz | ADR-0003, ADR-0008, ADR-0019, ADR-0020 |
| 6 — GUI | Hauptfenster, manueller Zuordnungs-Dialog, Tag-Verwaltung | ADR-0022, ADR-0023, ADR-0025, ADR-0028–0032 |
| 7 — Logging & Fehler | Diagnose-Logging, Config-Backups, Audit-Log, Fehlerbericht | ADR-0026, ADR-0033, ADR-0035 |
| 8 — Update-Lifecycle | Self-Update, Installer-Neustart | ADR-0045 |
| 9 — Build & Release | PyInstaller-Build, Inno-Setup-Installer, Release-Automatisierung, erstes Release v0.1.0 | ADR-0040, ADR-0041, ADR-0042 |
