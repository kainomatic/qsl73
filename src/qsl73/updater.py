# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Update-Prüfung und -Installation für QSL73. Tk-frei, nur HTTPS/GitHub."""
from __future__ import annotations

import hashlib
import logging
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

_log = logging.getLogger("qsl73.updater")

_GITHUB_API_URL = "https://api.github.com/repos/kainomatic/qsl73/releases"
_ALLOWED_ASSET_PREFIXES = (
    "https://github.com/",
    "https://objects.githubusercontent.com/",
)

# Altes Namensschema (≤ v0.2.0, unversioniert) — für Rückwärtskompatibilität erhalten.
STABLE_ASSET_NAME = "QSL73-Setup.exe"
BETA_ASSET_NAME = "QSL73-Beta-Setup.exe"

# Muster-Erkennung (ADR-0045 §13): deckt altes UND neues versioniertes Schema ab.
# Stable: ^QSL73-Setup(-vX.Y.Z)?\.exe$  — schließt Beta-Assets explizit aus.
# Beta:   ^QSL73-Beta-Setup(-vX.Y.Z)?\.exe$
_STABLE_ASSET_PATTERN = re.compile(r"^QSL73-Setup(-v\d+\.\d+\.\d+)?\.exe$")
_BETA_ASSET_PATTERN   = re.compile(r"^QSL73-Beta-Setup(-v\d+\.\d+\.\d+)?\.exe$")

# i18n-Vorbereitung
_ERR_NETWORK = "Keine Verbindung zur Update-Prüfung (Netzwerkfehler)."
_ERR_RATE_LIMIT = "GitHub-API-Rate-Limit — bitte später erneut prüfen."
_ERR_API = "GitHub-API-Fehler (HTTP {status})."
_ERR_NO_ASSET = "Kein passendes Installer-Asset im Release gefunden."
_ERR_SIZE_MISMATCH = (
    "Größenprüfung fehlgeschlagen: erwartet {expected} Bytes, erhalten {actual} Bytes — "
    "Installer wird nicht ausgeführt."
)
_ERR_INVALID_URL = "Asset-URL kommt nicht von einer erlaubten GitHub-Domain (HTTPS erwartet)."
_ERR_PARSE = "Fehler beim Auswerten der GitHub-API-Antwort."


class UpdateStatus(Enum):
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    ERROR = "error"


@dataclass
class AssetInfo:
    name: str
    url: str
    size: int  # Bytes laut API


@dataclass
class UpdateCheckResult:
    status: UpdateStatus
    new_version: Optional[str] = None    # z. B. "0.2.0"
    asset: Optional[AssetInfo] = None
    release_url: Optional[str] = None   # GitHub-Release-HTML-URL
    error_message: Optional[str] = None


def _parse_semver(tag: str) -> Optional[tuple[tuple[int, int, int], str]]:
    """Parst 'v0.1.0' → ((0,1,0), '') oder 'v0.2.0-beta1' → ((0,2,0), 'beta1').

    Gibt None bei ungültigem Format zurück.
    """
    if not tag.startswith("v"):
        return None
    rest = tag[1:]
    pre = ""
    if "-" in rest:
        base_str, pre = rest.split("-", 1)
    else:
        base_str = rest
    parts = base_str.split(".")
    if len(parts) != 3:
        return None
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2])), pre
    except ValueError:
        return None


def semver_gt(candidate_tag: str, current_version: str) -> bool:
    """True wenn candidate_tag neuer als current_version ist.

    current_version: ohne 'v'-Präfix (z. B. '0.1.0').
    candidate_tag:   mit 'v'-Präfix (z. B. 'v0.2.0' oder 'v0.2.0-beta1').

    Regel: vX.Y.Z-betaN < vX.Y.Z bei gleicher Basis.
    """
    cand = _parse_semver(candidate_tag)
    if cand is None:
        return False
    curr = _parse_semver(f"v{current_version}")
    if curr is None:
        return False
    cand_base, cand_pre = cand
    curr_base, curr_pre = curr
    if cand_base != curr_base:
        return cand_base > curr_base
    # Gleiche Basis: stable (pre="") > beta (pre!="")
    if curr_pre == "" and cand_pre == "":
        return False
    if curr_pre == "" and cand_pre != "":
        return False   # candidate ist beta desselben Release → nicht neuer
    if curr_pre != "" and cand_pre == "":
        return True    # candidate ist Stable, current ist beta → neuer
    return cand_pre > curr_pre  # beide beta → lexikografisch vergleichen


def _is_stable_tag(tag: str) -> bool:
    parsed = _parse_semver(tag)
    return parsed is not None and parsed[1] == ""


def _is_beta_tag(tag: str) -> bool:
    parsed = _parse_semver(tag)
    return parsed is not None and parsed[1] != ""


def _find_best_release(releases: list[dict], channel: str) -> Optional[dict]:
    """Neuestes passendes Release für den Kanal wählen."""
    candidates = []
    for r in releases:
        tag = r.get("tag_name", "")
        is_pre = bool(r.get("prerelease", False))
        if channel == "stable" and not is_pre and _is_stable_tag(tag):
            candidates.append(r)
        elif channel == "beta" and is_pre and _is_beta_tag(tag):
            candidates.append(r)
    if not candidates:
        return None

    def _sort_key(r: dict) -> tuple:
        parsed = _parse_semver(r.get("tag_name", ""))
        if parsed is None:
            return (0, 0, 0), ""
        base, pre = parsed
        # Leerer pre (stable) soll größer sortieren als jedes beta
        return base, ("\xff" if pre == "" else pre)

    candidates.sort(key=_sort_key, reverse=True)
    return candidates[0]


def _pick_asset(release: dict, channel: str) -> Optional[AssetInfo]:
    """Passendes Setup-Asset aus dem Release wählen (Muster-Erkennung, ADR-0045 §13).

    Erkennt altes (QSL73-Setup.exe) und neues versioniertes Schema (QSL73-Setup-vX.Y.Z.exe).
    Stable-Muster schließt Beta-Assets explizit aus.
    """
    pattern = _STABLE_ASSET_PATTERN if channel == "stable" else _BETA_ASSET_PATTERN
    for asset in release.get("assets", []):
        name = asset.get("name", "")
        if pattern.match(name):
            return AssetInfo(
                name=name,
                url=asset.get("browser_download_url", ""),
                size=int(asset.get("size", 0)),
            )
    return None


def _fetch_releases(timeout: int = 8) -> list[dict]:
    """GitHub-Releases-API abrufen. Wirft bei Netz- oder API-Fehlern."""
    import json

    req = urllib.request.Request(
        _GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "QSL73-Updater/1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = resp.status
        if status == 403:
            raise RuntimeError(_ERR_RATE_LIMIT)
        if status != 200:
            raise RuntimeError(_ERR_API.format(status=status))
        return json.loads(resp.read().decode("utf-8"))


def check_for_update(current_version: str, channel: str) -> UpdateCheckResult:
    """Prüft ob ein Update für den Kanal verfügbar ist.

    Non-fatal: Netzwerkfehler → UpdateStatus.ERROR, kein Crash.
    Nur HTTPS gegen api.github.com; kurzer Timeout.
    """
    try:
        releases = _fetch_releases()
    except urllib.error.URLError as exc:
        _log.debug("Update-Prüfung Netzwerkfehler: %s", exc)
        return UpdateCheckResult(status=UpdateStatus.ERROR, error_message=_ERR_NETWORK)
    except Exception as exc:
        _log.debug("Update-Prüfung fehlgeschlagen: %s", exc)
        return UpdateCheckResult(status=UpdateStatus.ERROR, error_message=str(exc))

    try:
        best = _find_best_release(releases, channel)
        if best is None:
            return UpdateCheckResult(status=UpdateStatus.UP_TO_DATE)
        tag = best.get("tag_name", "")
        if not semver_gt(tag, current_version):
            return UpdateCheckResult(status=UpdateStatus.UP_TO_DATE)
        asset = _pick_asset(best, channel)
        if asset is None:
            return UpdateCheckResult(
                status=UpdateStatus.ERROR,
                error_message=_ERR_NO_ASSET,
            )
        return UpdateCheckResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            new_version=tag.lstrip("v"),
            asset=asset,
            release_url=best.get("html_url"),
        )
    except Exception as exc:
        _log.debug("Update-Ergebnisauswertung fehlgeschlagen: %s", exc)
        return UpdateCheckResult(status=UpdateStatus.ERROR, error_message=_ERR_PARSE)


def _verify_asset_url(url: str) -> bool:
    """Prüft ob die URL von einer erlaubten GitHub-Domain kommt (HTTPS)."""
    return any(url.startswith(p) for p in _ALLOWED_ASSET_PREFIXES)


def download_update(
    asset: AssetInfo,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> Path:
    """Lädt das Asset nach %TEMP%, prüft Größe, gibt den Pfad zurück.

    Sicherheit: Nur erlaubte GitHub-Domains (HTTPS). Größenprüfung gegen
    den von der API gemeldeten Wert. Die GitHub-Releases-API liefert keinen
    kryptografischen Hash für Assets; SHA256 wird für Diagnosezwecke geloggt,
    kann aber nicht gegen einen Referenzwert verglichen werden.
    Bei Größenabweichung wird die Datei gelöscht und RuntimeError geworfen.

    on_progress: Callback(bytes_fertig, bytes_gesamt) — wird aus Download-Thread
    aufgerufen; Aufrufer muss ggf. ins UI-Thread delegieren.
    """
    if not _verify_asset_url(asset.url):
        raise RuntimeError(_ERR_INVALID_URL)

    tmp_path = Path(tempfile.gettempdir()) / f"qsl73_update_{uuid.uuid4().hex}.exe"
    req = urllib.request.Request(
        asset.url,
        headers={"User-Agent": "QSL73-Updater/1"},
    )

    downloaded = 0
    sha = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            with tmp_path.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    sha.update(chunk)
                    downloaded += len(chunk)
                    if on_progress is not None:
                        on_progress(downloaded, asset.size)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise

    _log.info(
        "Update heruntergeladen: %s (%d Bytes), SHA256=%s",
        tmp_path.name,
        downloaded,
        sha.hexdigest(),
    )

    actual = tmp_path.stat().st_size
    if asset.size > 0 and actual != asset.size:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(_ERR_SIZE_MISMATCH.format(expected=asset.size, actual=actual))

    return tmp_path


def launch_installer_and_exit(installer_path: Path, exit_fn: Callable[[], None]) -> None:
    """Startet den Installer (/SILENT /RESTARTQSL73) und beendet danach die App.

    Reihenfolge: Installer zuerst starten, dann App beenden.
    Der Installer kann QSL73.exe ersetzen, sobald sie nicht mehr läuft.

    /SILENT: zeigt Fortschrittsfenster, überspringt Assistent-Seiten.
    /RESTARTQSL73: Custom-Flag, das die .iss auswertet — löst den automatischen
    QSL73-Neustart nach dem Install aus (nur Self-Update-Pfad; interaktive
    Erstinstallation bekommt diesen Flag nicht und zeigt stattdessen eine Checkbox).
    UAC-Abfrage durch Windows ist unvermeidbar und akzeptiert.
    """
    _log.info("Starte Installer /SILENT /RESTARTQSL73: %s", installer_path)
    subprocess.Popen([str(installer_path), "/SILENT", "/RESTARTQSL73"])
    exit_fn()
