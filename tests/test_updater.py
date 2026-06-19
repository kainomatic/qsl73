# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für src/qsl73/updater.py — kein echter Netzcall, nur Mocks."""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qsl73.updater import (
    BETA_ASSET_NAME,
    STABLE_ASSET_NAME,
    AssetInfo,
    UpdateCheckResult,
    UpdateStatus,
    _find_best_release,
    _is_beta_tag,
    _is_stable_tag,
    _parse_semver,
    _pick_asset,
    _verify_asset_url,
    check_for_update,
    download_update,
    launch_installer_and_exit,
    semver_gt,
)


# ---------------------------------------------------------------------------
# _parse_semver
# ---------------------------------------------------------------------------

class TestParseSemver:
    def test_stable_tag(self):
        assert _parse_semver("v0.1.0") == ((0, 1, 0), "")

    def test_stable_tag_multidigit(self):
        assert _parse_semver("v1.10.3") == ((1, 10, 3), "")

    def test_beta_tag(self):
        assert _parse_semver("v0.2.0-beta1") == ((0, 2, 0), "beta1")

    def test_beta_tag_two_digit(self):
        assert _parse_semver("v0.2.0-beta12") == ((0, 2, 0), "beta12")

    def test_no_v_prefix(self):
        assert _parse_semver("0.1.0") is None

    def test_wrong_parts(self):
        assert _parse_semver("v0.1") is None

    def test_non_numeric(self):
        assert _parse_semver("vX.Y.Z") is None

    def test_empty(self):
        assert _parse_semver("") is None


# ---------------------------------------------------------------------------
# _is_stable_tag / _is_beta_tag
# ---------------------------------------------------------------------------

class TestTagClassifiers:
    def test_stable_true(self):
        assert _is_stable_tag("v0.1.0") is True

    def test_stable_false_for_beta(self):
        assert _is_stable_tag("v0.1.0-beta1") is False

    def test_beta_true(self):
        assert _is_beta_tag("v0.1.0-beta1") is True

    def test_beta_false_for_stable(self):
        assert _is_beta_tag("v0.1.0") is False

    def test_invalid_tag(self):
        assert _is_stable_tag("invalid") is False
        assert _is_beta_tag("invalid") is False


# ---------------------------------------------------------------------------
# semver_gt
# ---------------------------------------------------------------------------

class TestSemverGt:
    def test_newer_minor(self):
        assert semver_gt("v0.2.0", "0.1.0") is True

    def test_newer_patch(self):
        assert semver_gt("v0.1.1", "0.1.0") is True

    def test_newer_major(self):
        assert semver_gt("v1.0.0", "0.9.9") is True

    def test_same_version(self):
        assert semver_gt("v0.1.0", "0.1.0") is False

    def test_older_version(self):
        assert semver_gt("v0.0.9", "0.1.0") is False

    def test_beta_higher_base_is_newer(self):
        # v0.2.0-beta1 ist neuer als 0.1.0 (höhere Basis)
        assert semver_gt("v0.2.0-beta1", "0.1.0") is True

    def test_beta_same_base_not_newer_than_stable(self):
        # v0.1.0-beta1 ist NICHT neuer als 0.1.0 (gleiche Basis, beta < stable)
        assert semver_gt("v0.1.0-beta1", "0.1.0") is False

    def test_stable_newer_than_same_base_beta(self):
        # v0.1.0 ist neuer als 0.1.0-beta1 (stable > beta)
        assert semver_gt("v0.1.0", "0.1.0-beta1") is True

    def test_beta2_newer_than_beta1(self):
        # v0.2.0-beta2 > v0.2.0-beta1 (lexikografisch)
        assert semver_gt("v0.2.0-beta2", "0.2.0-beta1") is True

    def test_beta1_not_newer_than_beta2(self):
        assert semver_gt("v0.2.0-beta1", "0.2.0-beta2") is False

    def test_invalid_candidate(self):
        assert semver_gt("invalid", "0.1.0") is False

    def test_invalid_current(self):
        assert semver_gt("v0.2.0", "not-a-version") is False


# ---------------------------------------------------------------------------
# _find_best_release
# ---------------------------------------------------------------------------

def _make_release(tag: str, prerelease: bool, assets: list[dict] | None = None) -> dict:
    return {
        "tag_name": tag,
        "prerelease": prerelease,
        "html_url": f"https://github.com/kainomatic/qsl73/releases/tag/{tag}",
        "assets": assets or [],
    }


class TestFindBestRelease:
    def test_stable_picks_latest_stable(self):
        releases = [
            _make_release("v0.2.0", False),
            _make_release("v0.1.0", False),
        ]
        best = _find_best_release(releases, "stable")
        assert best is not None
        assert best["tag_name"] == "v0.2.0"

    def test_stable_ignores_beta(self):
        releases = [
            _make_release("v0.3.0-beta1", True),
            _make_release("v0.2.0", False),
        ]
        best = _find_best_release(releases, "stable")
        assert best is not None
        assert best["tag_name"] == "v0.2.0"

    def test_beta_picks_latest_prerelease(self):
        releases = [
            _make_release("v0.3.0-beta2", True),
            _make_release("v0.3.0-beta1", True),
            _make_release("v0.2.0", False),
        ]
        best = _find_best_release(releases, "beta")
        assert best is not None
        assert best["tag_name"] == "v0.3.0-beta2"

    def test_beta_ignores_stable(self):
        releases = [
            _make_release("v0.2.0", False),
        ]
        best = _find_best_release(releases, "beta")
        assert best is None

    def test_empty_releases(self):
        assert _find_best_release([], "stable") is None

    def test_invalid_tag_skipped(self):
        releases = [
            _make_release("not-a-tag", False),
            _make_release("v0.1.0", False),
        ]
        best = _find_best_release(releases, "stable")
        assert best is not None
        assert best["tag_name"] == "v0.1.0"


# ---------------------------------------------------------------------------
# _pick_asset
# ---------------------------------------------------------------------------

def _make_asset_entry(name: str, size: int = 1000) -> dict:
    return {
        "name": name,
        "browser_download_url": f"https://github.com/kainomatic/qsl73/releases/download/v0.2.0/{name}",
        "size": size,
    }


class TestPickAsset:
    def test_stable_picks_correct_asset(self):
        release = _make_release("v0.2.0", False, [
            _make_asset_entry(STABLE_ASSET_NAME, 42_000_000),
        ])
        asset = _pick_asset(release, "stable")
        assert asset is not None
        assert asset.name == STABLE_ASSET_NAME
        assert asset.size == 42_000_000

    def test_beta_picks_correct_asset(self):
        release = _make_release("v0.2.0-beta1", True, [
            _make_asset_entry(BETA_ASSET_NAME, 42_000_000),
        ])
        asset = _pick_asset(release, "beta")
        assert asset is not None
        assert asset.name == BETA_ASSET_NAME

    def test_stable_ignores_beta_asset(self):
        release = _make_release("v0.2.0", False, [
            _make_asset_entry(BETA_ASSET_NAME, 42_000_000),
        ])
        asset = _pick_asset(release, "stable")
        assert asset is None

    def test_no_assets_returns_none(self):
        release = _make_release("v0.2.0", False, [])
        assert _pick_asset(release, "stable") is None


# ---------------------------------------------------------------------------
# _verify_asset_url
# ---------------------------------------------------------------------------

class TestVerifyAssetUrl:
    def test_github_com_allowed(self):
        assert _verify_asset_url("https://github.com/kainomatic/qsl73/releases/download/v0.2.0/QSL73-Setup.exe") is True

    def test_objects_githubusercontent_allowed(self):
        assert _verify_asset_url("https://objects.githubusercontent.com/github-production-release-asset-12345/blob?token=abc") is True

    def test_http_not_allowed(self):
        assert _verify_asset_url("http://github.com/kainomatic/qsl73/releases/download/v0.2.0/QSL73-Setup.exe") is False

    def test_other_domain_not_allowed(self):
        assert _verify_asset_url("https://evil.example.com/QSL73-Setup.exe") is False

    def test_empty_url(self):
        assert _verify_asset_url("") is False


# ---------------------------------------------------------------------------
# check_for_update (mit gemockter API)
# ---------------------------------------------------------------------------

_ASSET_ENTRY = _make_asset_entry(STABLE_ASSET_NAME, 42_000_000)
_STABLE_RELEASES = [
    _make_release("v0.2.0", False, [_ASSET_ENTRY]),
    _make_release("v0.1.0", False, [_ASSET_ENTRY]),
]


def _mock_fetch(releases):
    """Patch-Helper: ersetzt _fetch_releases durch eine Funktion, die immer releases liefert."""
    return patch("qsl73.updater._fetch_releases", return_value=releases)


class TestCheckForUpdate:
    def test_update_available(self):
        with _mock_fetch(_STABLE_RELEASES):
            result = check_for_update("0.1.0", "stable")
        assert result.status == UpdateStatus.UPDATE_AVAILABLE
        assert result.new_version == "0.2.0"
        assert result.asset is not None
        assert result.asset.name == STABLE_ASSET_NAME

    def test_already_up_to_date(self):
        with _mock_fetch(_STABLE_RELEASES):
            result = check_for_update("0.2.0", "stable")
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_newer_than_available(self):
        with _mock_fetch(_STABLE_RELEASES):
            result = check_for_update("0.3.0", "stable")
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_network_error_returns_error_status(self):
        import urllib.error
        with patch("qsl73.updater._fetch_releases", side_effect=urllib.error.URLError("no network")):
            result = check_for_update("0.1.0", "stable")
        assert result.status == UpdateStatus.ERROR
        assert result.error_message is not None

    def test_api_exception_returns_error_status(self):
        with patch("qsl73.updater._fetch_releases", side_effect=RuntimeError("API error")):
            result = check_for_update("0.1.0", "stable")
        assert result.status == UpdateStatus.ERROR

    def test_no_matching_release_for_channel(self):
        # Stable releases, aber Beta-Kanal → kein Ergebnis → UP_TO_DATE
        with _mock_fetch(_STABLE_RELEASES):
            result = check_for_update("0.1.0", "beta")
        assert result.status == UpdateStatus.UP_TO_DATE

    def test_missing_asset_returns_error(self):
        # Release ohne passendes Asset
        releases = [_make_release("v0.2.0", False, [])]
        with _mock_fetch(releases):
            result = check_for_update("0.1.0", "stable")
        assert result.status == UpdateStatus.ERROR
        assert result.error_message is not None

    def test_beta_channel_finds_prerelease(self):
        beta_asset = _make_asset_entry(BETA_ASSET_NAME, 42_000_000)
        releases = [
            _make_release("v0.2.0", False, [_ASSET_ENTRY]),
            _make_release("v0.2.0-beta1", True, [beta_asset]),
        ]
        with _mock_fetch(releases):
            result = check_for_update("0.1.0", "beta")
        assert result.status == UpdateStatus.UPDATE_AVAILABLE
        assert result.asset is not None
        assert result.asset.name == BETA_ASSET_NAME

    def test_release_url_included(self):
        with _mock_fetch(_STABLE_RELEASES):
            result = check_for_update("0.1.0", "stable")
        assert result.release_url is not None
        assert "github.com" in result.release_url


# ---------------------------------------------------------------------------
# download_update (mit gemocktem HTTP)
# ---------------------------------------------------------------------------

class TestDownloadUpdate:
    def _make_fake_response(self, content: bytes, status: int = 200) -> MagicMock:
        resp = MagicMock()
        resp.status = status
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        chunks = [content[i:i+65536] for i in range(0, len(content), 65536)] + [b""]
        resp.read = MagicMock(side_effect=chunks)
        return resp

    def test_download_success(self, tmp_path):
        content = b"X" * 1000
        asset = AssetInfo(
            name=STABLE_ASSET_NAME,
            url=f"https://github.com/kainomatic/qsl73/releases/download/v0.2.0/{STABLE_ASSET_NAME}",
            size=len(content),
        )
        fake_resp = self._make_fake_response(content)
        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch("tempfile.gettempdir", return_value=str(tmp_path)):
            path = download_update(asset)
        assert path.exists()
        assert path.stat().st_size == len(content)

    def test_size_mismatch_raises_and_deletes(self, tmp_path):
        content = b"X" * 500
        asset = AssetInfo(
            name=STABLE_ASSET_NAME,
            url=f"https://github.com/kainomatic/qsl73/releases/download/v0.2.0/{STABLE_ASSET_NAME}",
            size=1000,  # Falsche Größe
        )
        fake_resp = self._make_fake_response(content)
        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch("tempfile.gettempdir", return_value=str(tmp_path)):
            with pytest.raises(RuntimeError, match="Größenprüfung"):
                download_update(asset)
        # Datei muss gelöscht sein
        remaining = list(tmp_path.glob("qsl73_update_*.exe"))
        assert remaining == []

    def test_invalid_url_raises(self):
        asset = AssetInfo(
            name=STABLE_ASSET_NAME,
            url="https://evil.example.com/fake.exe",
            size=1000,
        )
        with pytest.raises(RuntimeError, match="erlaubten GitHub-Domain"):
            download_update(asset)

    def test_progress_callback_called(self, tmp_path):
        content = b"X" * 1000
        asset = AssetInfo(
            name=STABLE_ASSET_NAME,
            url=f"https://github.com/kainomatic/qsl73/releases/download/v0.2.0/{STABLE_ASSET_NAME}",
            size=len(content),
        )
        fake_resp = self._make_fake_response(content)
        progress_calls = []
        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch("tempfile.gettempdir", return_value=str(tmp_path)):
            download_update(asset, on_progress=lambda d, t: progress_calls.append((d, t)))
        assert len(progress_calls) > 0
        assert progress_calls[-1][0] == len(content)

    def test_size_zero_skips_size_check(self, tmp_path):
        # size=0 → kein Größencheck (API hat keinen Wert geliefert)
        content = b"X" * 500
        asset = AssetInfo(
            name=STABLE_ASSET_NAME,
            url=f"https://github.com/kainomatic/qsl73/releases/download/v0.2.0/{STABLE_ASSET_NAME}",
            size=0,
        )
        fake_resp = self._make_fake_response(content)
        with patch("urllib.request.urlopen", return_value=fake_resp), \
             patch("tempfile.gettempdir", return_value=str(tmp_path)):
            path = download_update(asset)
        assert path.exists()


class TestLaunchInstallerAndExit:
    """launch_installer_and_exit übergibt /SILENT und /RESTARTQSL73."""

    def test_starts_installer_with_silent_and_restartqsl73(self, tmp_path):
        installer = tmp_path / "QSL73-Setup.exe"
        installer.write_bytes(b"")
        exit_calls = []
        with patch("subprocess.Popen") as mock_popen:
            launch_installer_and_exit(installer, lambda: exit_calls.append(True))
        assert mock_popen.call_count == 1
        args = mock_popen.call_args[0][0]
        assert str(installer) == args[0]
        assert "/SILENT" in args
        assert "/RESTARTQSL73" in args

    def test_calls_exit_fn_after_popen(self, tmp_path):
        installer = tmp_path / "QSL73-Setup.exe"
        installer.write_bytes(b"")
        order = []
        with patch("subprocess.Popen", side_effect=lambda *a, **kw: order.append("popen")):
            launch_installer_and_exit(installer, lambda: order.append("exit"))
        assert order == ["popen", "exit"]
