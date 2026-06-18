# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
# PyInstaller-Spec für QSL73 (onedir, console=False, 64-Bit)
# Erfordert: pyinstaller (NICHT in requirements.txt)
# Bauen: cd C:\Entwicklung\qsl73 && pyinstaller qsl73.spec

import sys
import os
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ---------------------------------------------------------------------------
# Bibliotheken bündeln
# ---------------------------------------------------------------------------

# tkcalendar + babel (reine Python, aber oft nicht auto-erkannt)
tkcalendar_datas, tkcalendar_binaries, tkcalendar_hiddenimports = collect_all('tkcalendar')
babel_datas, babel_binaries, babel_hiddenimports = collect_all('babel')

# pymupdf — native Lib (enthält mupdfcpp64.dll, _mupdf.pyd, _extra.pyd)
pymupdf_datas, pymupdf_binaries, pymupdf_hiddenimports = collect_all('pymupdf')

# fitz — API-Wrapper über pymupdf
fitz_datas, fitz_binaries, fitz_hiddenimports = collect_all('fitz')

# zxingcpp — einzelne .pyd-Datei (kein Package, daher manuell)
import zxingcpp as _zxing_mod
_zxing_pyd = _zxing_mod.__file__
zxing_binaries = [(_zxing_pyd, '.')]
zxing_hiddenimports = ['zxingcpp']
zxing_datas = []

# pywin32 (win32crypt, pywintypes etc. für DPAPI)
pywin32_datas, pywin32_binaries, pywin32_hiddenimports = collect_all('win32')

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

a = Analysis(
    ['run_qsl73.py'],
    pathex=['src'],
    binaries=(
        tkcalendar_binaries
        + babel_binaries
        + pymupdf_binaries
        + fitz_binaries
        + zxing_binaries
        + pywin32_binaries
    ),
    datas=(
        tkcalendar_datas
        + babel_datas
        + pymupdf_datas
        + fitz_datas
        + zxing_datas
        + pywin32_datas
        # Alle qsl73-Paketdateien (alle .py, kein separates TSV/CSV nötig)
    ),
    hiddenimports=(
        tkcalendar_hiddenimports
        + babel_hiddenimports
        + pymupdf_hiddenimports
        + fitz_hiddenimports
        + zxing_hiddenimports
        + pywin32_hiddenimports
        + [
            # Win32 / DPAPI
            'win32crypt',
            'win32api',
            'win32con',
            'winerror',
            'pywintypes',
            # GUI-Deps
            'tkcalendar',
            'babel',
            'babel.dates',
            'babel.numbers',
            # QR
            'zxingcpp',
            'fitz',
            'pymupdf',
            # qsl73 Module (sicherheitshalber explizit)
            'qsl73',
            'qsl73.gui',
            'qsl73.gui.app',
            'qsl73.gui.main_window',
            'qsl73.gui.controller',
            'qsl73.gui.setup_wizard',
            'qsl73.gui.wizard_logic',
            'qsl73.gui.filter_util',
            'qsl73.gui.manual_match',
            'qsl73.gui.manual_assignment',
            'qsl73.gui.error_dialog',
            'qsl73.gui.error_messages',
            'qsl73.gui.error_report_dialog',
            'qsl73.gui.config_error_dialog',
            'qsl73.data',
            'qsl73.data.itu_prefixes',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='QSL73',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/qsl73.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QSL73',
)
