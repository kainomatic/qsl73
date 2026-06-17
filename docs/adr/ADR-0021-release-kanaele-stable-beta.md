# ADR-0021: Release-Kanäle — Stable (main) und Beta (dev), parallel installierbar

**Status:** Accepted

## Kontext

QSL73 soll neue Features gefahrlos vorab testbar machen, ohne dass Nutzer die stabile
Produktiv-Installation riskieren. Damit der Beta-Kanal nicht aufdringlich wird, soll
er nicht bei jedem `dev`-Commit aktiv werden — nur bewusst markierte Vorab-Versionen
erscheinen als Beta-Update. Außerdem läuft Log4OM (und damit die SQLite-DB) auf dem
Rechner des Nutzers; wenn Stable und Beta denselben DB-Pfad eintragen, arbeitet auch
die experimentelle Beta gegen die produktive Datenbank — das muss erkennbar und
kommuniziert, aber nicht hard verhindert werden.

## Entscheidung

### 1. Zwei getrennte, parallel installierbare Programme

| | Stable | Beta |
|---|---|---|
| Quelle | `main`-Branch | `dev`-Branch |
| Installationspfad | `C:\Program Files\QSL73` | `C:\Program Files\QSL73 Beta` |
| Nutzerdaten | `%APPDATA%\QSL73\` | `%APPDATA%\QSL73-Beta\` |
| Installer | `QSL73-Setup.exe` | `QSL73-Beta-Setup.exe` |

Beide koexistieren auf demselben Rechner ohne gegenseitige Störung:
vollständig getrennte Config, Backups, Logs. Je ein eigener Installer.

### 2. Update-Kanäle (bewusst ruhig)

- **Stable** prüft gegen offizielle GitHub-Releases (Tag `vX.Y.Z`, aus `main`).
- **Beta** prüft **ausschließlich** gegen explizit getaggte GitHub-Pre-Releases (aus `dev`).
  Ein `dev`-Stand wird erst dann zum Beta-Update, wenn er als Pre-Release veröffentlicht
  wird — nicht bei jedem Commit oder Push.

### 3. BETA-Kennzeichnung

Die Beta-Variante trägt einen deutlich sichtbaren **„BETA"-Hinweis** in der Oberfläche
(mindestens Fenstertitel + „Über"-Dialog), damit jederzeit klar ist, welche Variante läuft.

### 4. Gemeinsamer Log4OM-DB-Pfad — Hinweis, keine Blockade

Es ist technisch möglich, dass der Nutzer in Stable und Beta denselben DB-Pfad einträgt.
Das wird **nicht verhindert** (DB liegt außerhalb QSL73; Nutzerentscheidung), aber
QSL73 weist klar darauf hin:
- beim Einrichten der Beta im Setup-Assistent, und/oder
- wenn die Beta erkennt, dass ihr DB-Pfad mit dem in einer vorhandenen
  Stable-Konfiguration identisch ist.

Empfehlung: Beta zunächst gegen eine DB-Kopie testen.
Das bestehende Sicherheitsnetz (Vor-Backup + Vorschau/Bestätigung, Schreibmodell B)
bleibt ohnehin wirksam.

## Konsequenzen

- **Schritt 8** (Update-Lifecycle): Update-Mechanismus muss den Kanal kennen und
  kanalabhängig prüfen (Stable → offizielle Releases; Beta → Pre-Releases).
- **Schritt 9** (Build/Installer): Zwei separate Inno-Setup-Konfigurationen mit
  eigenem Pfad, eigenem APPDATA-Verzeichnis und eigenem Produktnamen.
  BETA-Kennzeichnung in Fenstertitel und „Über"-Dialog.
  DB-Pfad-Hinweis im Setup-Assistent der Beta-Variante.
- Getrennte APPDATA-Verzeichnisse verhindern Config-/Log-/Backup-Konflikte.
- Nutzer können Stable und Beta gleichzeitig betreiben — kein gegenseitiges Stören.
- Das DB-Pfad-Risiko beim parallelen Betrieb liegt beim Nutzer; QSL73 warnt, blockiert nicht.
- BETA-Kennzeichnung verhindert Verwechslung der aktiven Variante.
