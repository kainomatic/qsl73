#!/usr/bin/env python3
"""
QSL73 — Über-Dialog-Diagnose-Skript  (tools/diag_about_dialog.py)

Baut den _on_about-Dialog ORIGINALGETREU nach — gleiche Widgets, gleiche Reihenfolge,
gleiche Logik wie main_window.py (dev-Stand inkl. resizable(True,True), after(1,_do_center),
load_about_logo, _compute_dialog_geometry). Kein Fix, kein Eingriff in src/.

Starten aus dem Repo-Root (venv aktiviert):
    python tools/diag_about_dialog.py

Ausgabedatei:
    Windows:    %TEMP%\\qsl73_about_diag.txt
    Linux/Mac:  /tmp/qsl73_about_diag.txt

Der Pfad wird am Anfang auf der Konsole ausgegeben und im Root-Fenster angezeigt.
"""
from __future__ import annotations

import platform
import sys
import tempfile
import tkinter as tk
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import ttk

# ─── 0.  src/ in sys.path ──────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR   = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# ─── 1.  Ausgabedatei ──────────────────────────────────────────────────────
OUTFILE = Path(tempfile.gettempdir()) / "qsl73_about_diag.txt"

# ─── 2.  Konstanten  (1 : 1 aus main_window.py) ───────────────────────────
VERSION = "0.3.0"
CHANNEL = "stable"

_ABOUT_TITLE        = "Über QSL73 — by DF1DS"
_ABOUT_DESC         = (
    "Gleicht gescannte Papier-QSL-Karten aus Paperless-ngx\n"
    "mit QSOs im Log4OM-Logbuch ab und markiert\n"
    "bestätigte Karten automatisch."
)
_ABOUT_LICENSE      = "Lizenz: GNU General Public License v3 (GPLv3)"
_ABOUT_AUTHOR_LABEL = "Autor:"
_ABOUT_AUTHOR       = "DF1DS | Stephan Dahmen | DOK: G16"
_ABOUT_LINK_GITHUB  = "GitHub"
_ABOUT_LINK_QRZ     = "QRZ.com"
_ABOUT_BTN_CLOSE    = "Schließen"
_ABOUT_URL_GITHUB   = "https://github.com/kainomatic/qsl73"
_ABOUT_URL_QRZ      = "https://www.qrz.com/db/DF1DS"
_ABOUT_MIN_H: int   = 520
_ABOUT_MIN_W: int   = 360

# ─── 3.  Hilfsfunktionen  (1 : 1 aus main_window.py) ─────────────────────
def _compute_dialog_geometry(dw: int, dh: int, px: int, py: int, pw: int, ph: int) -> str:
    x = max(0, px + (pw - dw) // 2)
    y = max(0, py + (ph - dh) // 2)
    return f"{dw}x{dh}+{x}+{y}"

# ─── 4.  Logging ──────────────────────────────────────────────────────────
_lines: list[str] = []

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def log(msg: str = "") -> None:
    line = (f"[{_ts()}]  {msg}") if msg else ""
    print(line)
    _lines.append(line)

def flush() -> None:
    try:
        OUTFILE.write_text("\n".join(_lines), encoding="utf-8")
    except Exception as exc:
        print(f"[WARN] Logdatei schreiben fehlgeschlagen: {exc}")

# ─── 5.  Widget-Snapshot-Helfer ──────────────────────────────────────────
def _snap_w(label: str, w: tk.Widget) -> None:
    try:
        log(
            f"    {label:<26} "
            f"mapped={str(w.winfo_ismapped()):<5}  "
            f"viewable={str(w.winfo_viewable()):<5}  "
            f"req={w.winfo_reqwidth()}x{w.winfo_reqheight()}  "
            f"act={w.winfo_width()}x{w.winfo_height()}"
        )
    except Exception as e:
        log(f"    {label:<26} FEHLER: {e}")


def snap_all(
    phase: str,
    dlg: tk.Toplevel,
    frame: ttk.Frame,
    children: list[tuple[str, tk.Widget]],
    last_geom: list[str],
) -> None:
    bar = "═" * max(1, 54 - len(phase))
    log()
    log(f"══ {phase} {bar}")
    try:
        log(
            f"  dlg   W={dlg.winfo_width():<5} H={dlg.winfo_height():<5} "
            f"x={dlg.winfo_x():<5} y={dlg.winfo_y():<5} "
            f"mapped={str(dlg.winfo_ismapped()):<5}  "
            f"viewable={str(dlg.winfo_viewable()):<5}"
        )
        log(f"  dlg   .geometry()   = {dlg.geometry()!r}")
        log(f"  dlg   (letztes set) = {last_geom[0]!r}")
    except Exception as e:
        log(f"  dlg: FEHLER: {e}")
    try:
        log(
            f"  frame reqW={frame.winfo_reqwidth():<5} reqH={frame.winfo_reqheight():<5} "
            f"actW={frame.winfo_width():<5} actH={frame.winfo_height():<5} "
            f"mapped={frame.winfo_ismapped()}"
        )
    except Exception as e:
        log(f"  frame: FEHLER: {e}")
    if children:
        log("  Kinder:")
        for name, child in children:
            _snap_w(name, child)
    flush()


# ─── 6.  Haupt-Diagnose ──────────────────────────────────────────────────
def run_diag() -> None:

    # ── Umgebungs-Info (vor Tk-Init) ─────────────────────────────────────
    log("╔══════════════════════════════════════════════════════════╗")
    log("║  QSL73 Über-Dialog Diagnose                              ║")
    log("╚══════════════════════════════════════════════════════════╝")
    log(f"Datum/Zeit:       {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}")
    log(f"Python:           {sys.version}")
    log(f"sys.executable:   {sys.executable}")
    log(f"Plattform:        {platform.platform()}")
    log(f"OS:               {platform.system()} {platform.release()}")
    log(f"Windows-Version:  {platform.version()}")

    # Tkinter-Modul-Konstanten (vor Tk()-Instanz verfügbar)
    try:
        log(f"Tk-Version:       {tk.TkVersion}")
        log(f"Tcl-Version:      {tk.TclVersion}")
    except Exception as e:
        log(f"Tk-Version:       FEHLER: {e}")

    # PIL / Pillow
    log()
    log("── PIL / Pillow-Status ─────────────────────────────────────────")
    for mod_name in ("PIL", "PIL.Image", "PIL.ImageTk"):
        try:
            m = __import__(mod_name, fromlist=[""])
            ver = getattr(m, "__version__", "?")
            log(f"  {mod_name:<16} verfügbar ({ver})")
        except ImportError as e:
            log(f"  {mod_name:<16} NICHT VERFÜGBAR ({e})")

    # Asset-Pfad prüfen (reine Datei-Prüfung, noch kein Tk nötig)
    asset_name = "qsl73_icon.png"
    if hasattr(sys, "_MEIPASS"):
        asset_path = Path(sys._MEIPASS) / asset_name
        log(f"  Bundle-Modus (_MEIPASS): {asset_path}")
    else:
        asset_path = SRC_DIR / "qsl73" / "assets" / asset_name
        log(f"  Dev-Modus:  {asset_path}")
    log(f"  Asset existiert: {asset_path.exists()}")

    logo_photo = None          # wird nach Tk-Init gesetzt
    logo_load_error: str = ""

    log()
    log(f"Ausgabedatei: {OUTFILE}")
    log("(Tk-Fenster wird geöffnet ...)")
    flush()

    # ── Root-Fenster ──────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("QSL73 Diagnose")
    root.geometry("680x155+60+60")

    ttk.Label(root, text="QSL73 Über-Dialog Diagnose", font=("", 12, "bold")).pack(pady=6)
    ttk.Label(root, text="Der Über-Dialog öffnet sich automatisch.").pack()
    ttk.Label(
        root,
        text=f"Log: {OUTFILE}",
        wraplength=660,
        justify="left",
        foreground="#555555",
    ).pack(pady=4)

    root.update_idletasks()
    root.update()

    # DPI / Skalierung (nach Tk-Init verfügbar)
    log()
    log("── Root-Fenster / DPI ──────────────────────────────────────────")
    log(
        f"  root  W={root.winfo_width():<5} H={root.winfo_height():<5} "
        f"x={root.winfo_x():<5} y={root.winfo_y():<5} "
        f"mapped={root.winfo_ismapped()}"
    )
    try:
        scaling = root.tk.call("tk", "scaling")
        ppi     = root.winfo_fpixels("1i")
        log(f"  tk scaling:   {scaling}  (1.0=96 DPI  1.25=120 DPI  1.5=144 DPI  2.0=192 DPI)")
        log(f"  Pixel/Inch:   {ppi:.1f}")
        log(f"  Bildschirm:   {root.winfo_screenwidth()} x {root.winfo_screenheight()} px")
        log(f"  Bildschirm:   {root.winfo_screenmmwidth()} x {root.winfo_screenmmheight()} mm")
    except Exception as e:
        log(f"  DPI-Info:     FEHLER: {e}")

    # ── Logo laden (nach Tk-Init — ImageTk.PhotoImage braucht Tk) ─────────
    log()
    log("── Logo-Laden (nach Tk-Init) ──────────────────────────────────")
    if not asset_path.exists():
        logo_load_error = f"Asset-Datei fehlt: {asset_path}"
        log(f"  → ÜBERSPRUNGEN: {logo_load_error}")
    else:
        try:
            from PIL import Image, ImageTk
            img   = Image.open(asset_path)
            log(f"  Image.open():       Größe={img.size}  Modus={img.mode}")
            img_r = img.resize((112, 112), Image.LANCZOS)
            log(f"  img.resize(112,112): Größe={img_r.size}")
            logo_photo = ImageTk.PhotoImage(img_r)
            log(f"  ImageTk.PhotoImage: {type(logo_photo).__name__}  → Logo GELADEN")
        except Exception as exc:
            logo_load_error = f"{type(exc).__name__}: {exc}"
            log(f"  FEHLER: {logo_load_error}")
            log("  Traceback:")
            for tline in traceback.format_exc().splitlines():
                log(f"    {tline}")

    log(f"  Ergebnis:  logo_photo = {'<PhotoImage>' if logo_photo is not None else 'None'}")
    flush()

    # ── Dialog aufbauen (1 : 1 wie _on_about) ─────────────────────────────
    log()
    log("── Dialog-Aufbau (1:1 wie _on_about) ──────────────────────────")

    last_geom: list[str] = ["(noch nicht gesetzt)"]
    children:  list[tuple[str, tk.Widget]] = []
    _closed    = [False]

    # --- gleicher Code wie _on_about ---
    dlg = tk.Toplevel(root)
    dlg.title(_ABOUT_TITLE)
    dlg.resizable(True, True)   # dev-Stand — False,False wäre der alte Bug
    dlg.transient(root)
    dlg.grab_set()
    log("  Toplevel(); resizable(True,True); transient(root); grab_set()")

    frame = ttk.Frame(dlg, padding=24)
    frame.pack(fill="both", expand=True)
    log("  frame = ttk.Frame(dlg, padding=24); frame.pack(fill='both', expand=True)")

    if logo_photo is not None:
        logo_lbl = tk.Label(frame, image=logo_photo, bg=frame.cget("background"))
        logo_lbl.image = logo_photo   # GC-Schutz
        logo_lbl.pack(pady=(0, 10))
        children.append(("logo_lbl", logo_lbl))
        log("  logo_lbl.pack(pady=(0,10))")
    else:
        log(f"  logo_lbl: ÜBERSPRUNGEN (logo_photo is None)")

    title_lbl = ttk.Label(
        frame, text=f"QSL73  v{VERSION}  ({CHANNEL})", font=("", 13, "bold")
    )
    title_lbl.pack(pady=(0, 14))
    children.append(("title_lbl", title_lbl))

    desc_lbl = ttk.Label(frame, text=_ABOUT_DESC, justify="center")
    desc_lbl.pack(pady=(0, 12))
    children.append(("desc_lbl", desc_lbl))

    sep_w = ttk.Separator(frame, orient="horizontal")
    sep_w.pack(fill="x", pady=(0, 12))
    children.append(("separator", sep_w))

    lic_lbl = ttk.Label(frame, text=_ABOUT_LICENSE)
    lic_lbl.pack(pady=(0, 6))
    children.append(("lic_lbl", lic_lbl))

    author_row = ttk.Frame(frame)
    author_row.pack(pady=(0, 14))
    children.append(("author_row", author_row))

    auth_lbl = ttk.Label(author_row, text=f"{_ABOUT_AUTHOR_LABEL}  ")
    auth_lbl.pack(side="left")
    children.append(("auth_lbl", auth_lbl))

    auth_name = tk.Label(author_row, text=_ABOUT_AUTHOR, font=("", 10, "bold"))
    auth_name.pack(side="left")
    children.append(("auth_name", auth_name))

    def _make_link(parent: tk.Misc, text: str, url: str) -> tk.Label:
        lbl = tk.Label(parent, text=text, fg="#0645ad", cursor="hand2", font=("", 9))
        lbl.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        lbl.bind("<Enter>",   lambda _e, l=lbl: l.config(font=("", 9, "underline")))
        lbl.bind("<Leave>",   lambda _e, l=lbl: l.config(font=("", 9)))
        return lbl

    link_row = ttk.Frame(frame)
    link_row.pack(pady=(0, 18))
    children.append(("link_row", link_row))

    gh_link = _make_link(link_row, _ABOUT_LINK_GITHUB, _ABOUT_URL_GITHUB)
    gh_link.pack(side="left", padx=(0, 20))
    children.append(("gh_link", gh_link))

    qrz_link = _make_link(link_row, _ABOUT_LINK_QRZ, _ABOUT_URL_QRZ)
    qrz_link.pack(side="left")
    children.append(("qrz_link", qrz_link))

    close_btn = ttk.Button(frame, text=_ABOUT_BTN_CLOSE)
    close_btn.pack()
    children.append(("close_btn", close_btn))

    dlg.minsize(_ABOUT_MIN_W, _ABOUT_MIN_H)
    log(f"  Alle Widgets gepackt. dlg.minsize({_ABOUT_MIN_W}, {_ABOUT_MIN_H})")
    # --- Ende _on_about-Block ---

    # ── Phase 1: Nach Widget-Aufbau, vor update_idletasks ─────────────────
    snap_all(
        "Phase 1 — Nach Widget-Aufbau, vor update_idletasks",
        dlg, frame, children, last_geom
    )

    dlg.update_idletasks()
    log(f"  dlg.update_idletasks() ausgeführt")

    # ── Phase 2: Nach update_idletasks ────────────────────────────────────
    snap_all("Phase 2 — Nach dlg.update_idletasks()", dlg, frame, children, last_geom)

    # Geometrie-Vorschau (exakt wie _do_center es berechnen wird)
    log()
    log("── Geometrie-Vorschau (wie _do_center — vor after(1)) ──────────")
    _sh       = dlg.winfo_screenheight()
    _sw       = dlg.winfo_screenwidth()
    _frq_h    = frame.winfo_reqheight()
    _frq_w    = frame.winfo_reqwidth()
    _dlg_rq_w = dlg.winfo_reqwidth()
    _needed_h = _frq_h + 90
    _cap_h    = int(_sh * 0.9)
    _tgt_h    = max(min(_needed_h, _cap_h), _ABOUT_MIN_H)
    _tgt_w    = max(_ABOUT_MIN_W, _dlg_rq_w)
    log(f"  screen:                  {_sw} x {_sh} px")
    log(f"  frame.winfo_reqheight()= {_frq_h}")
    log(f"  frame.winfo_reqwidth() = {_frq_w}")
    log(f"  dlg.winfo_reqwidth()   = {_dlg_rq_w}")
    log(f"  needed_h = reqH + 90   = {_needed_h}")
    log(f"  cap_h    = int(sh×0.9) = {_cap_h}")
    log(f"  target_h = max(min({_needed_h},{_cap_h}), {_ABOUT_MIN_H}) = {_tgt_h}")
    log(f"  target_w = max({_ABOUT_MIN_W}, {_dlg_rq_w}) = {_tgt_w}")
    log(f"  root.winfo_ismapped()  = {root.winfo_ismapped()}")
    flush()

    # ── after(1, _do_center)  — wie Original ──────────────────────────────
    def _do_center() -> None:
        if not dlg.winfo_exists():
            log("  _do_center: dlg nicht mehr vorhanden → Abbruch")
            flush()
            return

        log()
        log("── after(1, _do_center) ausgelöst ─────────────────────────────")
        dlg.update_idletasks()
        log("  dlg.update_idletasks() in _do_center ausgeführt")

        screen_h  = dlg.winfo_screenheight()
        needed_h  = frame.winfo_reqheight() + 90
        target_h  = min(needed_h, int(screen_h * 0.9))
        target_h  = max(target_h, _ABOUT_MIN_H)
        target_w  = max(_ABOUT_MIN_W, dlg.winfo_reqwidth())
        log(f"  frame.winfo_reqheight() = {frame.winfo_reqheight()}")
        log(f"  dlg.winfo_reqwidth()    = {dlg.winfo_reqwidth()}")
        log(f"  needed_h={needed_h}  target_h={target_h}  target_w={target_w}")

        geom = "(Fehler)"
        try:
            if root.winfo_ismapped():
                log("  root.winfo_ismapped()=True → zentriere über root")
                geom = _compute_dialog_geometry(
                    target_w, target_h,
                    root.winfo_rootx(), root.winfo_rooty(),
                    root.winfo_width(),  root.winfo_height(),
                )
            else:
                log("  root.winfo_ismapped()=False → zentriere auf Bildschirm")
                sw = dlg.winfo_screenwidth()
                x  = max(0, (sw - target_w) // 2)
                y  = max(0, (screen_h - target_h) // 2)
                geom = f"{target_w}x{target_h}+{x}+{y}"
        except Exception as exc:
            log(f"  FEHLER bei Geometrie-Berechnung: {exc}")
            log(traceback.format_exc())
            sw = dlg.winfo_screenwidth()
            x  = max(0, (sw - target_w) // 2)
            y  = max(0, (screen_h - target_h) // 2)
            geom = f"{target_w}x{target_h}+{x}+{y}"

        log(f"  → dlg.geometry({geom!r})")
        last_geom[0] = geom
        dlg.geometry(geom)

        snap_all(
            "Phase 3 — In after(1,_do_center) nach geometry()",
            dlg, frame, children, last_geom
        )

        # Verzögerte Messungen: 500 ms und 2000 ms
        dlg.after( 500, lambda: _snap_delayed("Phase 4 — 500 ms nach Öffnen"))
        dlg.after(2000, lambda: _snap_delayed("Phase 5 — 2000 ms nach Öffnen"))

    def _snap_delayed(label: str) -> None:
        if not dlg.winfo_exists():
            return
        snap_all(label, dlg, frame, children, last_geom)

    def _on_close() -> None:
        if _closed[0]:
            return
        _closed[0] = True

        snap_all(
            "Phase 6 — Beim Schließen (letzter Snapshot)",
            dlg, frame, children, last_geom
        )

        log()
        log("══ ZUSAMMENFASSUNG ══════════════════════════════════════════════")
        log(f"  Logo geladen:          {'JA' if logo_photo is not None else 'NEIN'}")
        if logo_load_error:
            log(f"  Logo-Fehler:           {logo_load_error}")
        log(f"  Letzte geometry()-Arg: {last_geom[0]!r}")
        try:
            log(f"  Finale dlg-Größe:      W={dlg.winfo_width()}  H={dlg.winfo_height()}")
            log(f"  Finale Position:       x={dlg.winfo_x()}  y={dlg.winfo_y()}")
            log(f"  dlg mapped:            {dlg.winfo_ismapped()}")
            all_ok = all(w.winfo_ismapped() for _, w in children if w.winfo_exists())
            log(f"  Alle Kinder mapped:    {all_ok}")
        except Exception as e:
            log(f"  Abschluss-Snapshot:    FEHLER: {e}")

        log()
        log("══ WAS DF1DS IN DER LOG-DATEI PRÜFEN SOLL ═════════════════════")
        log("  A) Logo geladen?")
        log("     JA  → Logo-Problem ausgeschlossen.")
        log("     NEIN → PIL fehlt oder Asset-Pfad falsch → Dialog öffnet ohne Logo,")
        log("            kann klein wirken wenn reqheight ohne Logo-Höhe berechnet wird.")
        log()
        log("  B) Phase 2 — frame.winfo_reqheight():")
        log("     Erwartung: > 300 (mit Logo: ~490 px); tatsächlich ohne Logo ~380 px.")
        log("     Wenn == 1 → update_idletasks() hat Layout nicht aufgelöst → Timing-Bug.")
        log()
        log("  C) Phase 3 — dlg.winfo_width() / winfo_height() nach geometry():")
        log("     Erwartung: stimmt mit target_w x target_h überein.")
        log("     Wenn NICHT → WM ignoriert geometry() trotz resizable(True,True)")
        log("     (könnte DPI-Virtualisierung auf Win10 sein).")
        log()
        log("  D) Alle Kinder mapped / viewable?")
        log("     Wenn NEIN → Widgets erzeugt aber NICHT gerendert.")
        log("     Das wäre der 'leer wenn manuell aufgezogen'-Befund.")
        log()
        log("  E) DPI-Skalierung (Root-Abschnitt):")
        log("     tk scaling > 1.0 deutet auf HiDPI hin. Tk hat dann evtl.")
        log("     falsche Koordinaten wenn DPI-Awareness nicht gesetzt ist.")
        log()
        log(f"  Ausgabedatei: {OUTFILE}")
        flush()

        dlg.destroy()
        root.after(300, root.destroy)

    close_btn.configure(command=_on_close)
    dlg.bind("<Escape>",           lambda _e: _on_close())
    dlg.protocol("WM_DELETE_WINDOW", _on_close)

    dlg.after(1, _do_center)

    print()
    print("=" * 64)
    print(f"  Diagnose läuft — Dialog offen bis 'Schließen' oder Esc.")
    print(f"  Log-Datei: {OUTFILE}")
    print("=" * 64)

    root.mainloop()

    flush()
    print()
    print(f"Diagnose abgeschlossen.  Log-Datei: {OUTFILE}")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    run_diag()
