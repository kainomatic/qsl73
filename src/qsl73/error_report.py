# src/qsl73/error_report.py
# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""On-demand-Fehlerbericht für QSL73 (§10, ADR-0035).

Reine Logik — tk-frei, testbar. Keine Secrets, keine QSO-Inhalte.

Öffentliche API:
  build_error_report   — Berichtstext aus Version/OS/Log
  build_github_url     — vorausgefüllte GitHub-Issue-URL
  open_in_browser      — Browser öffnen (kein Auto-Send)
  save_report_to_file  — Bericht lokal speichern
"""
from __future__ import annotations

import logging
import platform
import sys
import urllib.parse
import webbrowser
from pathlib import Path

_log = logging.getLogger("qsl73")

GITHUB_REPO = "kainomatic/qsl73"

_SECRET_KEYWORDS = (
    "token", "passwort", "password", "secret", "credential", "apikey", "api_key",
)


def _strip_secrets(text: str) -> str:
    """Entfernt Zeilen, die mögliche Secrets enthalten (case-insensitiv).

    Ersetzt betroffene Zeilen durch einen Platzhalter; lässt alle anderen Zeilen
    unverändert. Kein Regex — einfache Substring-Suche genügt für diesen Zweck.
    """
    result = []
    for line in text.splitlines():
        lower = line.lower()
        if any(kw in lower for kw in _SECRET_KEYWORDS):
            result.append("[Zeile gefiltert — mögliche sensible Daten]")
        else:
            result.append(line)
    return "\n".join(result)


def _read_last_log_lines(log_dir: Path, n: int = 50) -> str:
    """Liest die letzten n Zeilen aus qsl73.log; kein Absturz bei fehlender Datei."""
    log_path = log_dir / "qsl73.log"
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        return "\n".join(lines[-n:]) if lines else "(leer)"
    except OSError:
        return "(qsl73.log nicht vorhanden)"


def build_error_report(
    version: str,
    channel: str,
    log_dir: Path,
    qr_status: dict,
    n_lines: int = 50,
) -> str:
    """Baut einen bereinigten Fehlerbericht-Text.

    Enthält: App-Version/Channel, OS/Python, QR-Backend-Status, letzte n Log-Zeilen.
    Enthält NICHT: Secrets (Token/Passwort), QSO-Inhalte (aus audit.log bleibt draußen).
    """
    os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
    py_info = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    qr_info = (
        f"pymupdf (fitz)={qr_status.get('fitz', '?')}, "
        f"zxing-cpp={qr_status.get('zxing', '?')}"
    )
    raw_log = _read_last_log_lines(log_dir, n_lines)
    clean_log = _strip_secrets(raw_log)

    return (
        f"QSL73 Fehlerbericht\n"
        f"===================\n\n"
        f"Version:      {version} ({channel})\n"
        f"Betriebssystem: {os_info}\n"
        f"Python:       {py_info}\n"
        f"QR-Backend:   {qr_info}\n\n"
        f"--- Letzte {n_lines} Zeilen aus qsl73.log (bereinigt) ---\n"
        f"{clean_log}\n"
        f"--- Ende Log ---\n"
    )


def build_github_url(
    title: str,
    body: str,
    repo: str = GITHUB_REPO,
) -> str:
    """Baut eine vorausgefüllte GitHub-Issue-URL (URL-kodiert).

    Der Nutzer öffnet diese URL im Browser und entscheidet selbst über das Absenden.
    QSL73 sendet NICHTS automatisch.
    """
    params = urllib.parse.urlencode({"title": title, "body": body})
    return f"https://github.com/{repo}/issues/new?{params}"


def open_in_browser(url: str) -> None:
    """Öffnet eine URL im Standard-Browser. Kein Auto-Send — Nutzer entscheidet."""
    webbrowser.open(url)


def save_report_to_file(text: str, path: Path) -> None:
    """Schreibt den Berichtstext als UTF-8-Textdatei."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
