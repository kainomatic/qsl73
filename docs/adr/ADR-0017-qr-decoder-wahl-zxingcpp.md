# ADR-0017: QR-Decoder-Implementierung via zxingcpp statt pyzbar

**Status:** Accepted

## Kontext

ADR-0011 legt fest, dass QR-Codes client-seitig aus dem heruntergeladenen PDF
dekodiert werden (pymupdf → Rasterbild → QR-Decoder). Als Decoder-Bibliothek wurde
in ADR-0011 `pyzbar` als Beispiel genannt.

Im Schritt 4b wurde pyzbar (`0.1.9`) auf dem Dev-Rechner (Windows Server 2025,
Python 3.12 64-Bit) installiert, scheiterte aber beim Import mit:

```
FileNotFoundError: Could not find module
  'C:\...\pyzbar\libzbar-64.dll' (or one of its dependencies).
```

Das Python-Wheel enthält zwar `libzbar-64.dll` und `libiconv.dll`, aber
Windows Server 2025 findet die DLL-Abhängigkeiten über `ctypes.cdll.LoadLibrary`
nicht, weil das neuere Windows-DLL-Suchpfad-Modell (DLL-Isolation seit Win10/Server 2016)
Pfadergänzungen via PATH oder `os.add_dll_directory` in diesem Fall nicht greift.
Das bestehende Issue #7 deckt das bekannte Packaging-Problem für den späteren
PyInstaller-Build ab.

Als Alternative wurde `zxingcpp 3.0.0` geprüft: ein Python-Paket mit eingebetteter
C++-Bibliothek (ZXing-C++), das keine externe DLL benötigt und sofort importierbar ist.

## Entscheidung

`zxingcpp` (statt pyzbar) wird als QR-Decoder verwendet:

- `qr.py` importiert `zxingcpp` und `Pillow` (für das PIL-Bild-Zwischenformat).
- `pyzbar` bleibt in der Kommentar-Notiz in `requirements.txt` dokumentiert, wird
  aber nicht im Code verwendet.
- Die `decode_qr_from_pdf`-Funktion ist Soft-Dependency-tolerant: falls `zxingcpp`
  oder `pymupdf` nicht importierbar sind, gibt sie `None` zurück (kein Absturz).

### Toleranzregeln des QR-Parsers (§6.2)

`parse_qr_text` verwendet einen Split-basierten Key-Value-Parser:

- **Trennstrategie:** Splitten an `\s+` vor einem Schlüsselmuster (`[A-Za-z]\w*\s*:`)
- **Schlüssel:** case-insensitiv; Unterstrich-Schlüssel (Band_RX, Prop_Mode) werden korrekt
  erkannt; unbekannte Schlüssel (RST, QSL, Prop_Mode, …) werden still ignoriert.
- **Pflichtfelder:** `From`, `To`, `Date`, `Band`, `Mode` — fehlt eines → `None`.
- **Werte:** normalisiert durch `normalize_date`/`normalize_band`/`normalize_mode`;
  ein unbekannter Wert ergibt `None` im Feld, aber kein Absturz.
- **Feldreihenfolge:** beliebig (Dict-basiert, nicht positional).
- **Erstes gültiges QR:** Wenn mehrere QR-Codes auf einer Seite stehen (Werbe- + QSO-Code),
  wird der erste mit gültigem QSO-Format verwendet. Ungültige QR-Codes werden übersprungen.

## Konsequenzen

**Positiv:**
- Sofort lauffähig auf Windows Server 2025 ohne externe DLL-Abhängigkeit.
- Self-contained: alle Abhängigkeiten kommen aus dem Python-Wheel.
- Gleichwertige Dekodierqualität wie pyzbar für QR-Codes.

**Negativ / Risiken:**
- Abweichung von der pyzbar-Nennung in ADR-0011 (dort nur Beispiel, nicht verbindlich).
- pyzbar bleibt für den finalen PyInstaller-Bundle relevant (Issue #7) — falls das
  Bundle pyzbar einsetzen soll, muss die DLL-Situation noch gelöst werden.
  Für das Dev-Szenario ist zxingcpp die pragmatische Wahl.
- `zxingcpp` muss beim PyInstaller-Build aufgenommen werden (zieht das C++-Wheel mit).
