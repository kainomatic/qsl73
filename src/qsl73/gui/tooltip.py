# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Wiederverwendbare Hover-Tooltip-Infrastruktur für alle Fenster (ADR-0047).

Öffentliche API:
  attach_tooltip(widget, text, delay_ms=500)  — hängt Tooltip an ein beliebiges tk/ttk-Widget

Pure-Logik (testbar ohne Display):
  clamp_tooltip_position(x, y, w, h, screen_w, screen_h) → (x, y)
"""
from __future__ import annotations

_TOOLTIP_BG = "#ffffcc"
_TOOLTIP_FG = "#222222"
_TOOLTIP_BORDERWIDTH = 1
_TOOLTIP_FONT_SIZE = 8
_TOOLTIP_OFFSET_X = 10
_TOOLTIP_OFFSET_Y = 4
_TOOLTIP_DELAY_MS = 500


def clamp_tooltip_position(
    x: int, y: int, w: int, h: int, screen_w: int, screen_h: int
) -> tuple:
    """Klemmt Tooltip-Position so, dass er vollständig im Bildschirmbereich bleibt.

    Gibt (x, y) zurück.
    """
    if x + w + 4 > screen_w:
        x = screen_w - w - 4
    if y + h + 4 > screen_h:
        y = screen_h - h - 4
    if x < 0:
        x = 0
    if y < 0:
        y = 0
    return x, y


try:
    import tkinter as tk
    _TK_OK = True
except ImportError:
    _TK_OK = False


if _TK_OK:
    class _Tooltip:
        """Hover-Tooltip für ein tk/ttk-Widget.

        Einblenden nach delay_ms Verzögerung; ausblenden bei <Leave> oder <ButtonPress>.
        Crash-sicher: schnelles Hovern und Widget-Zerstörung während Anzeige → kein Absturz.
        """

        def __init__(self, widget: "tk.Widget", text: str, delay_ms: int = _TOOLTIP_DELAY_MS) -> None:
            self._widget = widget
            self._text = text
            self._delay_ms = delay_ms
            self._after_id = None   # ausstehende after()-ID oder None
            self._tip_win = None    # sichtbares Toplevel oder None

            widget.bind("<Enter>", self._on_enter, "+")
            widget.bind("<Leave>", self._on_leave, "+")
            widget.bind("<ButtonPress>", self._on_leave, "+")

        def _on_enter(self, _event=None) -> None:
            self._cancel_timer()
            self._after_id = self._widget.after(self._delay_ms, self._show)

        def _on_leave(self, _event=None) -> None:
            self._cancel_timer()
            self._hide()

        def _cancel_timer(self) -> None:
            if self._after_id is not None:
                try:
                    self._widget.after_cancel(self._after_id)
                except Exception:
                    pass
                self._after_id = None

        def _show(self) -> None:
            self._after_id = None
            if self._tip_win is not None:
                return
            try:
                x = self._widget.winfo_rootx() + _TOOLTIP_OFFSET_X
                y = self._widget.winfo_rooty() + self._widget.winfo_height() + _TOOLTIP_OFFSET_Y

                win = tk.Toplevel(self._widget)
                win.wm_overrideredirect(True)
                win.wm_attributes("-topmost", True)

                lbl = tk.Label(
                    win,
                    text=self._text,
                    background=_TOOLTIP_BG,
                    foreground=_TOOLTIP_FG,
                    relief="solid",
                    borderwidth=_TOOLTIP_BORDERWIDTH,
                    font=("", _TOOLTIP_FONT_SIZE),
                    padx=4,
                    pady=2,
                    justify="left",
                    wraplength=400,
                )
                lbl.pack()

                win.update_idletasks()
                tw = win.winfo_reqwidth()
                th = win.winfo_reqheight()
                sw = self._widget.winfo_screenwidth()
                sh = self._widget.winfo_screenheight()
                x, y = clamp_tooltip_position(x, y, tw, th, sw, sh)
                win.wm_geometry(f"+{x}+{y}")

                self._tip_win = win
            except Exception:
                pass

        def _hide(self) -> None:
            win = self._tip_win
            self._tip_win = None
            if win is not None:
                try:
                    win.destroy()
                except Exception:
                    pass

    def attach_tooltip(widget: "tk.Widget", text: str, delay_ms: int = _TOOLTIP_DELAY_MS) -> "_Tooltip":
        """Hängt einen Hover-Tooltip an widget.

        Speichert die Instanz auf dem Widget (_qsl73_tooltip) als GC-Schutz.
        Gibt das _Tooltip-Objekt zurück.
        """
        tip = _Tooltip(widget, text, delay_ms)
        widget._qsl73_tooltip = tip  # type: ignore[attr-defined]
        return tip

else:
    def attach_tooltip(widget, text: str, delay_ms: int = _TOOLTIP_DELAY_MS):  # type: ignore[misc]
        """No-op wenn tkinter nicht verfügbar (CI ohne Display)."""
        return None
