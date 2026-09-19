# QSL73 – ROADMAP

> Liefert **nur**, was keine andere Quelle liefert: aktueller Stand + priorisierte
> nächste Schritte. Offene Issues → GitHub (einzige Quelle). Änderungs-Details →
> CHANGELOG.md. Begründungen → docs/adr/. Rollen/Arbeitsablauf → CLAUDE.md.
> Wird **überschrieben**, nicht fortgeschrieben (kein neuer Absatz je Änderung).
> → ADR-0061

---

## A) Aktueller Stand

**v0.6.0-beta1 läuft (Tag auf `dev`, ADR-0046 §6).** `main` unverändert bei
`749eb2f` (Tag `v0.5.0`) — kein `main`-Eingriff, kein Stable-Tag (ADR-0065).
`__version__.py` = `0.6.0` (Ziel-Stable-Nummer), `CHANGELOG.md` `[Unreleased]`
bleibt bewusst offen bis zum Stable-Release. Stable-Freigabe erfolgt erst auf
ausdrückliche Ansage von DF1DS nach Desktop-Review (ADR-0065).

**Issue #41 (Eingangs-Tag als Arbeitskorb) umgesetzt** — Bestätigen und Ignorieren
entfernen den Eingangs-Tag jeweils in einem PATCH zusammen mit dem Bestätigt-/
Ignoriert-Tag; „Nicht mehr ignorieren" setzt ihn zurück. Übersprungene Karten
(`result.skipped`) bleiben unangetastet. Einmalige Alt-Bestand-Abfrage im
Hintergrund nach dem ersten Start (Queue-Polling-Muster, ADR-0023/ADR-0063) plus
dauerhafter Menüpunkt „Bearbeiten → Eingangs-Tag bei erledigten Karten
entfernen…" (ADR-0064). MINOR-Kandidat — Beta v0.6.0-beta1 s. o.

**Issue #40 (Tcl-Cross-Thread-Absturz im vollen Einzelprozess-Lauf) behoben** —
`tests/gui/` nutzt jetzt einen session-weiten tk-Root statt hunderter einzelner
`tk.Tk()`-Erzeugungen (ADR-0062). Voller `pytest -m "not slow"`-Lauf verifiziert
3× hintereinander stabil, voller `pytest`-Lauf grün. Der im Issue zusätzlich
vermerkte Produktivcode-Punkt ist ebenfalls erledigt: Die Update-Prüfung im
Hauptfenster ruft nicht mehr direkt `self.after(0, …)` aus dem Hintergrund-Thread
auf, sondern läuft über `RunController.start_update_check()` + Queue-Polling
(ADR-0063, ADR-0023-Muster).

Kein aktiver Bau-Auftrag.

Es wird auf keinen bestimmten Praxistest gewartet — nächster Schritt ist einer der
in Abschnitt B priorisierten Punkte (nach Praxistest der laufenden Beta).

---

## B) Nächste Schritte

Priorisierte Reihenfolge (DF1DS kann jederzeit umsortieren). Jede Nummer ist ein
GitHub-Issue.

1. **#35** / **#36** — Rufzeichen-Erkennung (Sonderrufzeichen zwei Ziffern; OCR O/0,
   I/1). Entscheidung DF1DS zum Falsch-Positiv-Risiko noch offen, erst ADR-Klärung.
2. **#42** — Werkzeug Bestätigungsübersicht. Grundentscheidungen bereits im Issue
   festgehalten (ADR-0060); Handtest DF1DS zu den exakten Log4OM-Strings noch
   ausstehend.
3. **#38** — Hauptfenster-Zeilen-Tooltip. Komfort-Feature, braucht Tooltip-Infrastruktur-
   Neubau (bestehende Infrastruktur bindet nur pro Widget, nicht pro Treeview-Zeile).
4. **#32** — Schutz gegen Direkt-Commits auf `main`. Prozess-/Doku-Thema, keine
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
