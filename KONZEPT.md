# QSL73 – Technische Spezifikation (KONZEPT.md)

> Fachliche Referenz für die Entwicklung. Beschreibt **was** QSL73 können muss und
> **wie** es sich verhalten soll – nicht die zeitliche Bau-Reihenfolge (→ ROADMAP.md).
> Maintainer/Entwickler: **DF1DS** (GitHub: kainomatic). Sprache der App: DE (Default),
> EN umschaltbar. Lizenz: MIT.
> Schreibmodell: Vorschau + Bestaetigung (kein separater dry-run; siehe §5/§7).

---

## 1. Zweck & Überblick

QSL73 ist ein Windows-Desktop-Tool (installierbare .exe), das gescannte **QSL-Karten
aus Paperless-ngx** automatisch mit den **QSOs im Log4OM-Logbuch (SQLite)** abgleicht
und bei sicherem Treffer das QSO als **Papier-QSL bestätigt** markiert. Zweifelsfälle
löst der Nutzer über einen **manuellen Zuordnungs-Bildschirm** mit Kartenanzeige.

Kernprinzipien:
- **Datensicherheit zuerst:** kein Schreibvorgang ohne Absicherung (WAL + Vor-Backup,
  Transaktion, definierte Schreibreihenfolge).
- **Transparenz:** "telefoniert nicht nach Hause"; nur 3 mögliche Verbindungen.
- **Nutzerkontrolle:** jeder Lauf zeigt erst eine Vorschau der geplanten Aenderungen und
  schreibt nur nach ausdruecklicher Bestaetigung; unsichere Faelle landen beim Menschen.

---

## 2. Systemumgebung

- **OS:** Windows 10 und 11, 64-Bit. (XP/8.1 nicht unterstützt.)
- **Sprache/Runtime:** Python 3.11+ (64-Bit), gebündelt via PyInstaller.
- **Installationsziel:** `C:\Program Files\QSL73` (pro Maschine, Adminrechte bei Installation).
- **Nutzerdaten:** `%APPDATA%\QSL73\` (config.yaml, logs\, backups\).
- **Externe Abhängigkeiten:** Log4OM (SQLite-DB lokal), Paperless-ngx (REST-API, erreichbar).

---

## 3. Datenquellen & Schnittstellen

### 3.1 Log4OM (SQLite)
- Standard-SQLite-Datei, vom Nutzer im Setup als Pfad angegeben.
- Zugriff **read+write**, Verbindung im **WAL-Modus** öffnen (technische Absturzsicherheit).
- **Discovery erforderlich** (an echter DB-Kopie, read-only): exakte Tabelle/Spalten für
  QSO-Felder (Rufzeichen, Datum/Zeit UTC, Band, Mode) und insbesondere das Feld/den Wert,
  der **„Papier-QSL bestätigt"** bedeutet (vs. eQSL/LoTW/QRZ). Schreibformat für
  „manuell bestätigt" exakt ermitteln, bevor geschrieben wird.
- Warnung ausgeben, wenn die DB in einem Cloud-Sync-Ordner (Dropbox/OneDrive) liegt.

### 3.2 Paperless-ngx (REST-API)
- Basis-URL vom Nutzer (vollständig inkl. http/https).
- **Auth:** Token ODER Benutzer/Passwort. Bei User/PW holt das Tool selbst einen Token via
  `POST /api/token/` und speichert **nur den Token** (DPAPI-verschlüsselt). Passwort wird
  nicht dauerhaft gespeichert.
- **OCR-Text:** `GET /api/documents/{id}/?fields=content`.
- **Dokument-Liste/Filter:** nach Tag (`qsl-card`) abrufen, paginiert.
- **Karten-Bild:** `GET /api/documents/{id}/preview/` (inline), `/download/` (Original,
  höhere Auflösung), `/thumb/` (Vorschau). Mehrseitiges PDF (Vorder-/Rückseite) zum Anzeigen
  in Bilder rendern.
- **Tag setzen/entfernen:** über das Document-Update-Endpoint (PATCH der Tag-Liste).

---

## 4. Konfiguration & Sicherheit

- Config-Datei: `%APPDATA%\QSL73\config.yaml`. Enthält: Paperless-URL, Auth-Modus,
  (verschluesselten) Token, Log4OM-DB-Pfad, Tag-Namen, Fuzzy an/aus, Sprache,
  Update-Check an/aus, Backup-Anzahl.
- **Token-Verschlüsselung:** Windows DPAPI (an Windows-Login gebunden), niemals Klartext.
- `config.example.yaml` als Vorlage im Repo; echte Config nie ins Repo (`.gitignore`).
- **Config-Migration:** beim ersten Start nach einem Update Pflicht – alte Config sauber
  auf neues Schema heben, mit Versionsfeld in der Config.

**Akzeptanzkriterien:**
- Frischer Start ohne Config → Setup-Assistent.
- Token liegt nur verschlüsselt vor (per Inspektion der config.yaml prüfbar).
- Ungültige/fehlende Felder führen zu klarer Fehlermeldung, nicht zum Absturz.

---

## 5. Verarbeitungsablauf (ein Lauf)

Es gibt einen Lauf-Typ mit eingebauter Vorschau und Bestaetigung (kein separater
dry-run-Modus).

1. Sammeln: Alle Paperless-Dokumente mit Tag `qsl-card` abrufen, OCR-Text holen.
2. Parsen: Aus dem OCR-Text Kandidatenwerte extrahieren (Rufzeichen, Datum, Band, Mode).
3. Vorfilter Log4OM: Nur QSOs als Match-Kandidaten, deren Papier-QSL noch NICHT bestaetigt
   ist. eQSL/LoTW/QRZ etc. werden weder gelesen-als-Grund noch geschrieben.
4. Matchen (siehe §6): pro Karte Ergebnis sicher / unsicher / kein Match.
5. Vorschau anzeigen: Geplante Bestaetigungen (sichere Auto-Treffer) sowie die unsicheren
   und kein-Match-Karten werden angezeigt; Zusammenfassung z. B. '12 wuerden bestaetigt,
   5 unsicher, 3 kein Match'. Noch nichts geschrieben.
6. Manuell ergaenzen (optional): Im selben Durchgang kann der Nutzer unsichere Karten ueber
   den manuellen Zuordnungs-Bildschirm zuordnen (§9). Diese manuellen Zuordnungen kommen in
   denselben Korb geplanter Aenderungen wie die automatischen sicheren Treffer.
7. Bestaetigen & Schreiben: Erst auf Klick 'Jetzt schreiben' laeuft EINE gesammelte
   Transaktion fuer ALLE geplanten Aenderungen (auto + manuell) zusammen: Vor-Backup ->
   DB-Transaktion -> Paperless-Tags (§7). 'Abbrechen' verwirft alles ohne Aenderung.
8. Abschluss: Ergebnis/Logeintrag; verbleibende unsichere/kein-Match-Karten bleiben in der
   Liste bzw. kommen beim naechsten Lauf erneut zur Wiedervorlage.

**Akzeptanzkriterien:**
- Vor dem Klick 'Jetzt schreiben' wird garantiert nichts geschrieben (weder DB noch Tags),
  aber die vollstaendige Vorschau ist erzeugt.
- 'Abbrechen' hinterlaesst DB und Tags unveraendert.
- Auto-Treffer und manuelle Zuordnungen werden in EINER Transaktion gemeinsam geschrieben.
- Bereits Papier-QSL-bestaetigte QSOs erscheinen nie als Kandidat.

---

## 6. Matching-Logik

- **Auto-Bestätigung nur**, wenn **Rufzeichen + Datum + Band + Mode** übereinstimmen.
- **Datum exakt.** Rufzeichen/Band/Mode mit **Fuzzy-Toleranz von 1 Zeichen** (gegen
  OCR-Verleser); Fuzzy in den Einstellungen abschaltbar.
- Ergebnis je Karte:
  - **sicher** = genau ein Kandidat erfüllt alle vier Felder → bestätigen.
  - **unsicher** = ein oder mehrere Kandidaten vorhanden, aber nicht eindeutig (z. B.
    nur teilweise Übereinstimmung, mehrere mögliche QSOs) → Tag `qsl-nicht-bestätigt`.
  - **kein Match** = kein plausibler Kandidat → **kein Status-Tag** (Wiedervorlage).
- "kein Match" ≠ "nicht bestätigt" (unterschiedliche Zustände, getrennt behandeln).

**Akzeptanzkriterien:**
- Ein QSO mit exakt passenden vier Feldern wird als „sicher" erkannt.
- Ein um 1 Zeichen abweichendes Rufzeichen (bei sonst exakter Übereinstimmung) matcht bei
  Fuzzy=an als „sicher", bei Fuzzy=aus als „unsicher" oder „kein Match".
- Zwei gleich gut passende Kandidaten ergeben „unsicher", nie eine Auto-Bestätigung.

---

## 7. Schreibstrategie (Datensicherheit)

- **WAL-Modus** für technische Absturzsicherheit (selbstheilend bei Abbruch).
- **Erst sammeln (inkl. Vorschau+Bestaetigung), dann gesammelt schreiben:** alle Aenderungen
  - automatische sichere Treffer UND manuelle Zuordnungen - nach Klick 'Jetzt schreiben' in
  **einer SQLite-Transaktion** (alles-oder-nichts, kein halb geschriebener Zustand).
- **Reihenfolge:** (1) DB-Transaktion erfolgreich, DANN (2) Paperless-Tags setzen.
  - DB scheitert → keine Tags (kein Widerspruch).
  - Nur Tag-Setzen scheitert → QSO korrekt bestätigt; fehlendes Tag wird beim nächsten
    Lauf nachgezogen.
- **Vor-Backup nur beim tatsaechlichen Schreiben** (Klick 'Jetzt schreiben'); reines
  Ansehen/Abbrechen oder 'nichts zu schreiben' -> kein Backup. Schuetzt vor inhaltlichen
  Fehlern (falsche Zuordnung), wogegen WAL nicht hilft.
- **Backup-Aufbewahrung:** konfigurierbar, **Default 5**, ältere automatisch löschen.
  Einstellungen zeigen Hinweis + Live-Speicheranzeige der Backups + „Backup-Ordner öffnen".

**Akzeptanzkriterien:**
- Simulierter Abbruch mitten im Schreiben → DB bleibt im Zustand vor dem Lauf (Transaktion).
- Nach erfolgreichem commit existiert genau ein neues Vor-Backup; Anzahl respektiert das Limit.
- Tags werden nie gesetzt, wenn die DB-Transaktion fehlgeschlagen ist.

---

## 8. Paperless-Tags (Setup-Defaults, anpassbar)

- `qsl-card` → zu verarbeitende Karten (nur diese werden gelesen).
- `qsl-bestätigt` → gesetzt bei sicherem Match ODER nach manueller Zuordnung.
- `qsl-nicht-bestätigt` → gesetzt nur bei unsicherem/mehrdeutigem Treffer.
- kein Status-Tag → bei „kein Match" (Wiedervorlage).
- Tag-Namen im Setup frei wählbar (für bestehende Paperless-Installationen).

---

## 9. GUI (tkinter)

- **Sprache:** DE Default, EN umschaltbar (Einstellungen).
- **Optik:** schlicht/sachlich, heller Standard-Look; Programm-Icon (Titelleiste/Startmenü/EXE).
- **Single-Instance:** nur eine laufende Instanz (Lock), kein paralleles DB-Schreiben.
- **Hauptbereich:** Lauf starten; laufende Konsolen-/Log-Ausgabe inkl. Netzwerkaktionen
  live; nach dem Matchen Vorschau der geplanten Aenderungen + Buttons 'Jetzt schreiben' /
  'Abbrechen'.
- **Ergebnis-Liste:** lightweight Filter „unsicher" / „kein Match" / „beides". Muss mit
  sehr vielen Einträgen flüssig bleiben.
- **Manueller Zuordnungs-Bildschirm (Kern-Feature):**
  - Karten-Bild (Vorder-/Rückseite), **erst beim Anklicken** der Karte nachladen.
  - Eingabefelder daneben, mit OCR-Vorschlag vorbefüllt (z. B. Rufzeichen).
  - **Live-Suche während des Tippens** gegen die Log4OM-DB: passende QSOs (Datum/Band/Mode)
    sofort als Vorschläge; Nutzer wählt das richtige QSO und ordnet zu.
  - Manuelle Zuordnung = wie Auto-Match: QSO markieren + Tag `qsl-bestätigt`.
- **Fehler-Prompt:** verständliche Kurzmeldung mit **aufklappbarem Detailbereich** (Stacktrace).
- **Setup-Assistent** beim ersten Start; alle Werte später in **Einstellungen** änderbar.
- **Hilfe → „Über / Datenschutz"-Dialog:** listet die 3 Verbindungen, stellt klar dass keine
  Daten an den Entwickler gehen, nennt lokale Speicherorte, verlinkt das Repo; Buttons
  „Log-Ordner öffnen", „Backup-Ordner öffnen"; Kontakt: GitHub-Issues + QRZ-Link
  (https://www.qrz.com/db/DF1DS).

**Akzeptanzkriterien:**
- Zweite Programminstanz startet nicht (oder fokussiert die bestehende).
- Liste mit z. B. 2000 Einträgen scrollt/filtert ohne spürbare Verzögerung; Bilder erst on click.
- Live-Suche zeigt bei Eingabe eines gültigen Rufzeichens die passenden QSOs.

---

## 10. Logging & Fehler-Reporting

- Zwei Logs in `%APPDATA%\QSL73\logs\`:
  - `audit.log` → fachliche Änderungen (Zeitstempel, Dok-ID, QSO Rufzeichen/Datum/Band/Mode,
    auto vs. manuell, Backup ja/nein).
  - `qsl73.log` → technisches Diagnose-Log mit Leveln (INFO/WARNING/ERROR).
- **Log-Rotation:** Maximalgröße pro Datei, Archiv-Rotation, nur wenige behalten.
- **Fehler-Reporting on demand** (kein Auto-Versand, kein Account-Zwang):
  - „Auf GitHub melden" → vorausgefülltes Issue im Browser (Account nötig).
  - „Bericht lokal speichern/teilen" → Datei ablegen; Nutzer entscheidet über Weitergabe.
  - Bericht **bereinigt**: nur QSL73-Version, Windows-Version, Fehlertyp/Stacktrace,
    Aktionskontext. KEINE Tokens/Passwörter/URL/QSO-Inhalte. Nutzer sieht ihn vor Versand.
- **Kein eingebettetes Token** in der App.

**Akzeptanzkriterien:**
- Ein provozierter Fehler erzeugt einen Logeintrag in `qsl73.log` und einen aufklappbaren Prompt.
- Der generierte Bericht enthält nachweislich keine Secrets/QSO-Inhalte.

---

## 11. „Telefoniert nicht nach Hause"

- Keine Telemetrie, keine Daten an Entwickler/zentralen Server.
- Genau 3 mögliche Verbindungen: (1) eigenes Paperless, (2) lokale Log4OM-Datei (kein Netz),
  (3) GitHub – ausschließlich für Update-Prüfung/Download.
- Automatische Update-Prüfung in den Einstellungen abschaltbar.

---

## 12. Update-Lifecycle

- **Prüfung:** beim Start (abschaltbar) + Button „Auf Updates prüfen", gegen die
  **GitHub-Releases-API** (Tag `vX.Y.Z` + Release Notes).
- **Flow:** Hinweis mit neuen Features → „Jetzt"/„Später". Bei „Jetzt": Installer laden →
  eigener **Updater** startet, QSL73 schließt sich → Updater zeigt Fortschritt, führt den
  **Inno-Installer still** aus (ersetzt nur Geändertes, räumt Altes weg) → Erfolg → „OK"
  startet die neue Version.
- **Config-Migration** beim ersten Start nach Update (siehe §4).

**Akzeptanzkriterien:**
- Bei vorhandener neuerer Release-Version erscheint der Hinweis inkl. Release-Notes.
- Nach Update läuft die neue Version, alte/überflüssige Dateien sind entfernt, Config migriert.

---

## 13. Installer / Deinstaller (Inno Setup)

- Installation pro Maschine nach `C:\Program Files\QSL73`; sauber in Registry,
  Windows-Deinstallationsliste, Startmenü. Programm-Icon eingebunden.
- **Kein Autostart** – nur manueller Start.
- **Deinstaller** entfernt Programmdateien, Registry-Einträge, Verknüpfungen restlos und
  **fragt**, ob Nutzerdaten (`%APPDATA%\QSL73`) ebenfalls gelöscht werden sollen.

**Akzeptanzkriterien:**
- Nach Deinstallation (ohne Nutzerdaten-Löschung) sind nur noch `%APPDATA%\QSL73` Daten übrig.
- Mit Nutzerdaten-Löschung bleibt nichts zurück.

---

## 14. Versionierung & Doku (von Claude Code geführt)

- **SemVer MAJOR.MINOR.PATCH.** PATCH=Bugfix, MINOR=neue Funktion (abwärtskompatibel),
  MAJOR=Bruch (z. B. Config ohne Migration). Immer nur eine Stelle erhöhen, niedrigere auf 0.
- Veröffentlichte Releases nie nachträglich ändern → nur neue Version.
- Start `0.x.y`; erste stabile/benutzbare Version = `1.0.0`.
- **CHANGELOG.md** im Repo pflegen. Eingebaute Version = Git-Tag = GitHub-Release; Changelog,
  Release-Notes und Tag konsistent.

---

## 15. Repo, Lizenz, Branding

- GitHub öffentlich, Account **kainomatic**, Repo z. B. `qsl73`. Branches: `main` (stabil),
  `dev` (laufend), `feature/*` (von `dev`).
- Keine Secrets im Repo: `.gitignore` + `config.example.yaml`.
- **Lizenz MIT** (`LICENSE`-Datei). Inhaber-Infos (DF1DS, kainomatic, QRZ-Link) im
  „Über"-Dialog, EXE-Metadaten, `LICENSE`, `README`.
- **Logo/Icon:** Originaldatei `qsl73logo.png` in `qsl73-assets/`. Freistellen +
  `.ico`-Erzeugung (alle Größen; 16/24/32px ggf. vereinfachtes Motiv aus Pfeilen+Haken,
  ab 48px volles Logo) durch Claude Code mit geeignetem Tool – nicht per Skript-Threshold
  (erzeugt Halos). Farben: Blau ~#3A78A6, Grün ~#4FA75E.

---

## 16. Tech-Stack

Python 3.11+ (64-Bit), `requests` (Paperless), `sqlite3` (Log4OM, WAL), `rapidfuzz` (Fuzzy),
`PyYAML` (Config), `tkinter` (GUI), `pywin32` (DPAPI), Bild-/PDF-Anzeige (`Pillow` + PDF-Render).
Build: **PyInstaller** → **Inno Setup**. Hinweis: unsignierte EXE löst SmartScreen-Warnung aus.

---

## 17. Bewusst verschoben (V2)

- **Undo** einer Bestätigung (QSO wiederfinden, Status zurücksetzen, Paperless-Tag entfernen).
  Fuer Start nicht noetig (Vorschau+Bestaetigung + Vor-Backup sichern ab).
