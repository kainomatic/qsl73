# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für _compute_dialog_geometry, _resolve_dialog_height, _resolve_dialog_width
und die _ABOUT_MIN_H/_ABOUT_MIN_W-Konstanten (tk-frei).

Der tk-Test am Ende benötigt ein Display; er wird übersprungen wenn keines verfügbar ist.
"""
import pytest

from qsl73.gui.main_window import (
    _ABOUT_MIN_H,
    _ABOUT_MIN_W,
    _compute_dialog_geometry,
    _resolve_dialog_height,
    _resolve_dialog_width,
)


# ---------------------------------------------------------------------------
# _compute_dialog_geometry
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("dw,dh,px,py,pw,ph,expected", [
    # Dialog kleiner als Parent → zentriert
    (340, 200, 100, 100, 800, 600, "340x200+330+300"),
    # Dialog so groß wie Parent → Position = Parent-Ursprung
    (800, 600, 100, 100, 800, 600, "800x600+100+100"),
    # Dialog größer als Parent → negative Vorwerte werden auf 0 geclippt
    (1000, 800, 50, 50, 800, 600, "1000x800+0+0"),
    # Parent nahe linkem Rand (x würde negativ) → 0
    (400, 300, 10, 200, 200, 400, "400x300+0+250"),
    # Minimalfall: alles 0
    (100, 50, 0, 0, 0, 0, "100x50+0+0"),
    # Über-Dialog höher als Parent (520 > 450): y wird auf 0 geclippt, x korrekt zentriert
    (360, 520, 0, 0, 750, 450, "360x520+195+0"),
    # Über-Dialog höher als Parent, Parent nicht am oberen Rand (py=50):
    # y = max(0, 50+(450-520)//2) = max(0, 50-35) = 15
    (360, 520, 100, 50, 750, 450, "360x520+295+15"),
])
def test_compute_dialog_geometry(dw, dh, px, py, pw, ph, expected):
    assert _compute_dialog_geometry(dw, dh, px, py, pw, ph) == expected


def test_compute_dialog_geometry_dialog_taller_than_parent_x_not_zero():
    """Wenn Dialog höher als Parent ist (y wird geclippt), bleibt x korrekt zentriert.

    Regression: Dialog darf nicht bei x=0 landen, nur weil y auf 0 geclippt wird.
    """
    # Parent bei x=100, Breite 750 → x sollte 100 + (750-360)//2 = 295 sein, nicht 0
    geom = _compute_dialog_geometry(360, 520, 100, 50, 750, 450)
    parts = geom.split("+")
    x = int(parts[1])
    assert x == 295, f"x={x} erwartet 295 — Dialog fälschlicherweise nach links verschoben"


# ---------------------------------------------------------------------------
# _ABOUT_MIN_H / _ABOUT_MIN_W — Konstanten-Invarianten
# ---------------------------------------------------------------------------

def test_about_min_h_covers_logo_plus_content():
    """_ABOUT_MIN_H muss Logo (112 px) + gesamten Inhalt + Chrome (90 px) abdecken.

    Untere Schranke: Logo+pady(122) + Titel(36) + Beschr(62) + Sep(16) + Lizenz(26)
    + Autor(34) + Links(38) + Button(25) + Padding(48) + Chrome(90) ≈ 497 px.
    _ABOUT_MIN_H muss ≥ 490 sein.
    """
    assert _ABOUT_MIN_H >= 490, (
        f"_ABOUT_MIN_H={_ABOUT_MIN_H} ist zu klein — "
        "muss Logo+Inhalt+Chrome (≥490 px) abdecken"
    )


def test_about_min_w_covers_logo():
    """_ABOUT_MIN_W muss Logo (112 px) + Frame-Padding (48 px) aufnehmen können."""
    assert _ABOUT_MIN_W >= 200, (
        f"_ABOUT_MIN_W={_ABOUT_MIN_W} ist zu klein für Logo (112) + Padding (48)"
    )


# ---------------------------------------------------------------------------
# _resolve_dialog_height
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inner_h,chrome,min_h,expected", [
    # Normaler Fall: Inhalt + Chrome ergibt sinnvolle Höhe über der Mindesthöhe
    (300, 40, 200, 340),
    # Fehlerfall: unrealistisch kleine Höhe (z. B. 1 vom Toplevel-minsize-Artefakt)
    # → Mindesthöhe greift, kein 1px-Fenster
    (1, 40, 300, 300),
    # Kleiner Wert + Chrome noch unterhalb der Mindesthöhe → Mindesthöhe greift
    (50, 40, 300, 300),
    # Großer Inhalt → Mindesthöhe greift nicht
    (400, 40, 300, 440),
    # Chrome = 0
    (200, 0, 150, 200),
    # Über-Dialog-Muster: chrome=90, min_h=_ABOUT_MIN_H (520)
    (411, 90, 520, 520),   # frame=411 (mit Logo) → 501 < 520 → Minimum greift
    (450, 90, 520, 540),   # frame=450 → 540 > 520 → Inhalt bestimmt
    (1, 90, 520, 520),     # 1px-Timing-Artefakt → hartes Minimum greift
    (285, 90, 520, 520),   # frame ohne Logo (285) → 375 < 520 → Minimum greift
])
def test_resolve_dialog_height(inner_h, chrome, min_h, expected):
    assert _resolve_dialog_height(inner_h, chrome=chrome, min_h=min_h) == expected


def test_resolve_dialog_height_default_prevents_1px():
    """Regressionstest: Messwert 1 (minsize-Artefakt) → finale Höhe >= Standard-Mindesthöhe."""
    result = _resolve_dialog_height(1)
    assert result >= 300


def test_resolve_dialog_height_about_min_h_with_1px():
    """Über-Dialog: 1px-Artefakt → finale Höhe >= _ABOUT_MIN_H (Logo-inklusive Mindesthöhe)."""
    result = _resolve_dialog_height(1, chrome=90, min_h=_ABOUT_MIN_H)
    assert result >= _ABOUT_MIN_H, (
        f"Höhe {result} < _ABOUT_MIN_H={_ABOUT_MIN_H} — hartes Minimum greift nicht"
    )


def test_resolve_dialog_height_about_min_h_without_logo_in_frame():
    """Wenn frame.winfo_reqheight() Logo nicht einschließt (285 px), greift _ABOUT_MIN_H."""
    # Simuliert Win10-Timing: frame meldet Höhe OHNE Logo (~285 px)
    result = _resolve_dialog_height(285, chrome=90, min_h=_ABOUT_MIN_H)
    assert result >= _ABOUT_MIN_H, (
        f"Höhe {result} < _ABOUT_MIN_H={_ABOUT_MIN_H} — "
        "Dialog zu klein wenn Logo nicht in frame-Messung enthalten"
    )


# ---------------------------------------------------------------------------
# _resolve_dialog_width
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("inner_w,min_w,expected", [
    # Mindestbreite greift wenn inner_w kleiner
    (1, 360, 360),
    (200, 360, 360),
    (359, 360, 360),
    # inner_w größer → kein Clipping
    (360, 360, 360),
    (500, 360, 500),
    # Anderer min_w
    (100, 480, 480),
    (600, 480, 600),
])
def test_resolve_dialog_width(inner_w, min_w, expected):
    assert _resolve_dialog_width(inner_w, min_w=min_w) == expected


def test_resolve_dialog_width_default_prevents_1px():
    """Regressionstest: Messwert 1 → finale Breite >= Standard-Mindestbreite."""
    result = _resolve_dialog_width(1)
    assert result >= 360


def test_resolve_dialog_width_default_min():
    """Standard-Mindestbreite (360) — Logo + Texte + Buttons passen sicher hinein."""
    assert _resolve_dialog_width(0) == 360
    assert _resolve_dialog_width(359) == 360
    assert _resolve_dialog_width(361) == 361


def test_resolve_dialog_width_about_min_w():
    """_ABOUT_MIN_W-Messwert 1 → finale Breite >= _ABOUT_MIN_W."""
    result = _resolve_dialog_width(1, min_w=_ABOUT_MIN_W)
    assert result >= _ABOUT_MIN_W


# ---------------------------------------------------------------------------
# Tk-Test — benötigt echtes Display; skippt wenn nicht verfügbar
# ---------------------------------------------------------------------------

def _tk_available() -> bool:
    """Prüft ob Tkinter ein Fenster öffnen kann (kein Headless-Fallback)."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.destroy()
        return True
    except Exception:
        return False


_SKIP_TK = pytest.mark.skipif(
    not _tk_available(),
    reason="Kein Display verfügbar — tk-Test übersprungen",
)


@_SKIP_TK
def test_about_dialog_opens_at_minimum_size():
    """Über-Dialog erreicht _ABOUT_MIN_W/H — auch ohne Logo (None) und mit Logo.

    Testet das reale tk-Verhalten: Dialog wird mit und ohne Logo geöffnet, Breite/Höhe
    nach dem Mapping gemessen. Prüft außerdem dass Position >= (0,0) (kein oben-links-Bug).
    """
    import tkinter as tk
    from tkinter import ttk

    def _open_dialog(with_logo: bool) -> dict:
        root = tk.Tk()
        root.geometry("900x700+50+50")
        root.update()
        root.deiconify()
        root.update_idletasks()

        measured: dict = {}

        dlg = tk.Toplevel(root)
        dlg.title("Test-Über-Dialog")
        dlg.resizable(True, True)  # Fix: False,False lässt WM die geometry()-Größe ignorieren
        dlg.transient(root)

        frame = ttk.Frame(dlg, padding=24)
        frame.pack(fill="both", expand=True)

        if with_logo:
            try:
                from qsl73.gui._icon import load_about_logo
                logo_photo = load_about_logo(size=112)
                if logo_photo is not None:
                    logo_lbl = tk.Label(frame, image=logo_photo)
                    logo_lbl.image = logo_photo
                    logo_lbl.pack(pady=(0, 10))
            except Exception:
                pass

        ttk.Label(frame, text="QSL73  v0.2.3  (stable)", font=("", 13, "bold")).pack(pady=(0, 14))
        ttk.Label(frame, text="Beschreibung\nmehrzeilig\nZeile3", justify="center").pack(pady=(0, 12))
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(frame, text="Lizenz: GPLv3").pack(pady=(0, 6))

        author_row = ttk.Frame(frame)
        author_row.pack(pady=(0, 14))
        ttk.Label(author_row, text="Autor:  ").pack(side="left")
        tk.Label(author_row, text="DF1DS | Stephan Dahmen", font=("", 10, "bold")).pack(side="left")

        link_row = ttk.Frame(frame)
        link_row.pack(pady=(0, 18))
        tk.Label(link_row, text="GitHub", fg="#0645ad").pack(side="left", padx=(0, 20))
        tk.Label(link_row, text="QRZ.com", fg="#0645ad").pack(side="left")

        ttk.Button(frame, text="Schliessen", command=dlg.destroy).pack()

        dlg.minsize(_ABOUT_MIN_W, _ABOUT_MIN_H)
        dlg.update_idletasks()

        def _do_center():
            if not dlg.winfo_exists():
                return
            dlg.update_idletasks()
            screen_h = dlg.winfo_screenheight()
            needed_h = frame.winfo_reqheight() + 90
            target_h = min(needed_h, int(screen_h * 0.9))
            target_h = max(target_h, _ABOUT_MIN_H)
            target_w = max(_ABOUT_MIN_W, dlg.winfo_reqwidth())
            if root.winfo_ismapped():
                geom = _compute_dialog_geometry(
                    target_w, target_h,
                    root.winfo_rootx(), root.winfo_rooty(),
                    root.winfo_width(), root.winfo_height(),
                )
            else:
                sw = dlg.winfo_screenwidth()
                x = max(0, (sw - target_w) // 2)
                y = max(0, (screen_h - target_h) // 2)
                geom = f"{target_w}x{target_h}+{x}+{y}"
            dlg.geometry(geom)
            dlg.after(80, _measure)

        def _measure():
            if dlg.winfo_exists():
                measured["w"] = dlg.winfo_width()
                measured["h"] = dlg.winfo_height()
                measured["x"] = dlg.winfo_x()
                measured["y"] = dlg.winfo_y()
            dlg.destroy()

        dlg.after(1, _do_center)
        root.after(3000, lambda: [dlg.destroy() if dlg.winfo_exists() else None])
        dlg.wait_window()
        root.destroy()
        return measured

    # Test 1: mit Logo
    m = _open_dialog(with_logo=True)
    assert "w" in m, "Dialog (mit Logo) nicht korrekt gemessen"
    assert m["w"] >= _ABOUT_MIN_W, f"Breite {m['w']} < _ABOUT_MIN_W={_ABOUT_MIN_W}"
    assert m["h"] >= _ABOUT_MIN_H, f"Höhe {m['h']} < _ABOUT_MIN_H={_ABOUT_MIN_H}"
    assert m["x"] >= 0, f"x={m['x']} negativ — Dialog links vom Bildschirmrand"
    assert m["y"] >= 0, f"y={m['y']} negativ — Dialog oberhalb des Bildschirms"

    # Test 2: ohne Logo (simuliert load_about_logo → None auf Systemen ohne PIL)
    m2 = _open_dialog(with_logo=False)
    assert "w" in m2, "Dialog (ohne Logo) nicht korrekt gemessen"
    assert m2["w"] >= _ABOUT_MIN_W, f"Breite {m2['w']} < _ABOUT_MIN_W={_ABOUT_MIN_W}"
    assert m2["h"] >= _ABOUT_MIN_H, (
        f"Höhe {m2['h']} < _ABOUT_MIN_H={_ABOUT_MIN_H} — "
        "hartes Minimum muss auch ohne Logo gelten"
    )
    assert m2["x"] >= 0, f"x={m2['x']} negativ"
    assert m2["y"] >= 0, f"y={m2['y']} negativ"


# ---------------------------------------------------------------------------
# TEIL 1 — Diagnosetest: resizable(False,False) ignoriert geometry()
# ---------------------------------------------------------------------------

@_SKIP_TK
def test_resizable_false_vs_true_geometry():
    """Belegt die Wurzelursache: resizable(False,False) ignoriert explizite geometry()-Größe.

    Öffnet denselben minimalen Dialog einmal mit resizable(False,False) und einmal mit
    resizable(True,True), jeweils mit identischem geometry("700x600+50+50")-Aufruf.
    Erwartet: True,True respektiert die gesetzte Größe; False,False lässt den WM
    die natürliche Pack-Größe verwenden (deutlich kleiner als 700x600 auf Windows).

    Der True,True-Zweig ist die harte Assertion; der False,False-Zweig wird nur
    gemessen und als Diagnosewert zurückgegeben — WM-Verhalten kann plattformabhängig sein.
    """
    import tkinter as tk
    from tkinter import ttk

    TARGET_W, TARGET_H = 700, 600
    GEOM = f"{TARGET_W}x{TARGET_H}+50+50"

    def _open_with(resizable: bool) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.update_idletasks()

        measured: dict = {}

        dlg = tk.Toplevel(root)
        dlg.title("Diagnose-Dialog")
        dlg.resizable(resizable, resizable)

        # Minimaler Inhalt: ein Label
        ttk.Label(dlg, text="Diagnose").pack(padx=20, pady=20)

        dlg.update_idletasks()
        dlg.geometry(GEOM)

        def _measure():
            if dlg.winfo_exists():
                dlg.update_idletasks()
                measured["w"] = dlg.winfo_width()
                measured["h"] = dlg.winfo_height()
            dlg.destroy()

        dlg.after(120, _measure)
        root.after(3000, lambda: [dlg.destroy() if dlg.winfo_exists() else None])
        dlg.wait_window()
        root.destroy()
        return measured

    m_false = _open_with(resizable=False)
    m_true = _open_with(resizable=True)

    assert "w" in m_true, "Diagnosemessung (True,True) fehlgeschlagen"
    assert "w" in m_false, "Diagnosemessung (False,False) fehlgeschlagen"

    # resizable(True,True): geometry() muss respektiert werden
    assert m_true["w"] == TARGET_W, (
        f"resizable(True,True): Breite {m_true['w']} ≠ {TARGET_W} — "
        "geometry() wurde nicht respektiert"
    )
    assert m_true["h"] == TARGET_H, (
        f"resizable(True,True): Höhe {m_true['h']} ≠ {TARGET_H} — "
        "geometry() wurde nicht respektiert"
    )

    # resizable(False,False): nur messen, kein harter Größenvergleich (WM-abhängig)
    # Auf Windows ist erwartet: m_false["w"] << TARGET_W (WM ignoriert geometry())
    # Auf manchen Linux-WMs kann False,False trotzdem greifen → kein harter Assert
    _ = (m_false["w"], m_false["h"])  # Werte für Diagnosezwecke verfügbar
