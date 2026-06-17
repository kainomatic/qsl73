# ADR-0024: Python 3.12 als hart gesetzte Referenzversion

**Status:** Accepted

## Kontext

Beim ersten Realtest (2026-06-17, Win10) scheiterte Python 3.14 an fehlendem
zxing-cpp-Wheel (`No matching distribution found` für die cp314-Plattform).
zxing-cpp ist die einzige native Abhängigkeit im kritischen QR-Decode-Pfad und
muss als vorgebautes Wheel verfügbar sein, da ein Compile aus dem Source auf
Endnutzer-Maschinen nicht zumutbar ist. Ebenso benötigt pywin32 (DPAPI) ein
plattformspezifisches Wheel.

## Entscheidung

Python **3.12** ist die hart gesetzte Referenzversion für Entwicklung und Build.

Begründung:
- Stabile Wheels für alle nativen Abhängigkeiten verfügbar: zxing-cpp 3.0.0
  (cp312-Wheel), pywin32, pymupdf.
- Python 3.12 wird bis Oktober 2028 mit Security-Updates versorgt.
- Realtest bestätigt: `pip install zxing-cpp` mit Python 3.12 → zxing-cpp 3.0.0,
  funktioniert einwandfrei.

Bei einem künftigen Versionssprung (3.13, 3.14, …) vorher prüfen:
1. Breaking Changes in der Python-Standardbibliothek und den Abhängigkeiten.
2. Wheel-Verfügbarkeit für zxing-cpp **und** pywin32 auf der Zielversion.
Bis zur expliziten Ablösung dieser Entscheidung bleibt 3.12 die Referenz.

## Konsequenzen

+ Reproduzierbare Builds: alle Entwickler und die CI verwenden dieselbe Version.
+ Wheel-Garantie: zxing-cpp und pywin32 sind als vorgebaute Binaries verfügbar.
+ Laufzeitunterstützung bis ca. 2028 — kein baldiger Handlungsbedarf.
- Neuere Python-Features (3.13+) können nicht genutzt werden.
- Bei Sicherheitslücken in 3.12 muss der Wechsel ggf. vorgezogen werden
  (dann Wheel-Prüfung wiederholen).
- Der Windows-Installer (Schritt 9) muss explizit Python 3.12 einbetten;
  "neueste Python-Version" ist kein gültiges Buildkriterium.
