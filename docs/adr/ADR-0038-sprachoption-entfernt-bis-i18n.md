# ADR-0038: Sprachoption im Einstellungen-Dialog entfernt bis i18n existiert

**Status:** Accepted

## Kontext

Das Config-Modell enthält `app.language` (Werte: `de`, `en`; Default: `de`).
Der SetupWizard bot bisher ein Auswahlfeld „Sprache" an. Das Feld hat jedoch keine
Wirkung, da keine i18n-Infrastruktur existiert und alle GUI-Texte fest auf Deutsch
verdrahtet sind. Nutzern wurde eine Funktion angeboten, die nicht existiert.

## Entscheidung

Das Sprach-Auswahlfeld wird aus dem SetupWizard/Einstellungen-Dialog entfernt.

- **Config-Modell bleibt unverändert**: `app.language` existiert weiterhin mit
  Default `"de"`. Bestehende `config.yaml`-Dateien laden ohne Fehler; das Feld
  wird beim Laden toleriert und beim Speichern im Bearbeiten-Modus erhalten
  (weil `collect_overrides` nur Felder aus `self._vars` liefert und das Feld
  dort nicht mehr registriert ist → `merge_wizard_overrides` behält den Altwert).
- **Kein Anzeigen = kein falsches Versprechen.** Bis eine echte i18n-Infrastruktur
  existiert, wird keine Sprachoption angeboten.
- Nutzersichtbare Texte werden in den GUI-Modulen als Modul-Konstanten gesammelt
  (bereits begonnen), um die spätere Übersetzungsarbeit zu erleichtern.
- Issue #25 dokumentiert die V2-Aufgabe: Infrastruktur einführen, Texte extrahieren,
  englische Übersetzung erstellen, Sprachumschaltung reaktivieren.

## Konsequenzen

**Positiv:**
- Keine wirkungslose Option mehr im Einstellungen-Dialog.
- Bestehende Configs bleiben vollständig kompatibel.

**Negativ / Einschränkungen:**
- Mehrsprachigkeit erst in V2 verfügbar (bewusste Entscheidung, kein Versehen).
