# ADR-0037: Durcharbeiten-Workflow für manuelle Zuordnung (UNCERTAIN → NO_MATCH)

**Status:** Accepted

## Kontext

Issue #24 (Paket 2, TEIL C): Bisher öffnet ein Doppelklick auf eine UNCERTAIN- oder
NO_MATCH-Karte einen Dialog mit nur zwei Buttons („Übernehmen" / „Abbrechen"). Für
einen effizienten Arbeitsablauf bei mehreren ungeklärten Karten fehlt eine
Durcharbeiten-Möglichkeit, die automatisch von Karte zu Karte springt.

Zusätzlich fehlten im Dialog sichtbare Statusinformationen (UNCERTAIN/NO_MATCH-Anzeige
mit Farbe, Fortschritt „Karte X von Y").

## Entscheidung

### 1. Workflow-Architektur (Sequenzsteuerung im MainWindow)

Die Sequenzsteuerung liegt in `main_window.py`, der Dialog bleibt per-Karte modal.

- `ManualAssignmentDialog` bekommt 4 Buttons: **Speichern** (ersetzt „Übernehmen"),
  **Speichern und nächste**, **Nächste**, **Abbrechen**.
- Das neue Attribut `action: str` gibt den Abschlussgrund zurück:
  `"save"`, `"save_next"`, `"skip"`, `"cancel"`.
- `MainWindow._on_double_click` öffnet den Dialog mit Workflow-Kontext (Phase,
  Fortschritt, has_next) und startet bei `"save_next"` / `"skip"` den Iterationsloop
  via `_continue_workflow()`.

Alternativen verworfen:
- **Dialog-interne Sequenz**: Dialog wäre für die Sequenzsteuerung verantwortlich
  und würde andere Karten direkt öffnen → verletzt Single-Responsibility.
- **Separater Workflow-Controller**: Überentwicklung für einen klar abgrenzbaren
  Anwendungsfall.

### 2. Phasenreihenfolge und Übergänge

Phase 1: alle offenen UNCERTAIN-Karten der Reihe nach.
Phase 2 (optional): alle offenen NO_MATCH-Karten.

Der Phasenübergang UNCERTAIN → NO_MATCH wird über einen `messagebox.askyesno`-Dialog
gesteuert, nicht über einen Button im Zuordnungs-Dialog (Nutzer soll bewusst entscheiden).

### 3. Button-Zustände

| Button | Aktiviert wenn |
|--------|---------------|
| Speichern | QSO in Treeview ausgewählt |
| Speichern und nächste | QSO ausgewählt UND `has_next=True` |
| Nächste | `has_next=True` (immer, ohne Selektion) |
| Abbrechen | immer |

„Nächste" und „Speichern und nächste" sind ausgegraut wenn `has_next=False` (letzte
Karte der Phase). Der Phasenübergang wird nach „Speichern" auf der letzten Karte
über den Ja/Nein-Dialog gesteuert.

### 4. Reine Logik-Funktionen (testbar, ohne tk)

`filter_util.py` erhält zwei neue reine Funktionen:
- `build_workflow_sequence(displayed, done)` → `(uncertain_offen, no_match_offen)`
- `workflow_card_context(card, uncertain, no_match)` → Kontext-Dict für den Dialog

### 5. Statusanzeige im Dialog

Wenn `card_index > 0`: Statusleiste am oberen Rand des Dialogs mit:
- Farbiger Phase-Beschriftung: „Unsicher" (orange) / „Kein Treffer" (grau)
- Fortschritt: „Karte X von Y"

### 6. Über-Dialog (TEIL B)

`messagebox.showinfo` in `_on_about` ersetzt durch custom `tk.Toplevel` ohne
Systemsound. Enthält klickbare Links (GitHub, QRZ.com) via `webbrowser.open`.

### 7. Setup-Wizard — Fenstergröße und Attention-Handler (TEIL A)

**A1 — Fenstergröße:** `_adjust_window_size()` wird via `self.after(1, ...)` nach dem
ersten Mapping aufgerufen. Inhaltshöhe aus `self._inner_frame.winfo_reqheight()` statt
`self.winfo_reqheight()` (welche vor dem Mapping 0 zurückgibt). Zentrierung über
sichtbarem Parent-Fenster, falls vorhanden.

**A2 — Attention-Handler:** FocusIn/FocusOut-Ansatz entfernt (funktioniert nicht
zuverlässig bei grab_set). Stattdessen `<Button-1>`-Bindung am Parent-Fenster mit
Funcid-Referenz, die beim Schließen sauber gelöst wird. Im Erstkonfigurationsmodus
(Parent nicht sichtbar via `winfo_ismapped()`) wird kein Handler gesetzt.

## Konsequenzen

**Positiv:**
- Effizienter Durcharbeiten-Workflow für mehrere UNCERTAIN/NO_MATCH-Karten.
- Sichtbarer Status (Phase + Fortschritt) im Dialog.
- Kein Systemsound im Über-Dialog.
- Klickbare Links im Über-Dialog.
- Korrekte Fenstergröße und -position des Setup-Wizards.
- Attention-Handler funktioniert zuverlässig (Parent-Binding).

**Negativ / Einschränkungen:**
- Der Workflow kann durch „Speichern" mitten in einer Phase beendet werden (Nutzer
  muss den nächsten Doppelklick manuell auslösen). Das ist ein Feature, kein Bug.
- Übersprungene Karten (via „Nächste") werden in diesem Workflow-Lauf nicht erneut
  gezeigt. Beim nächsten Doppelklick (neuer Lauf) erscheinen sie wieder.
