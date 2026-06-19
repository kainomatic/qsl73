# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für gui/doc_paths.py — tk-frei."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from qsl73.gui.doc_paths import get_fallback_url, resolve_doc_html


class TestResolveDocHtml:
    def test_returns_path_when_file_exists(self, tmp_path):
        html = tmp_path / "LIESMICH.html"
        html.write_text("<html/>", encoding="utf-8")
        with patch("sys.executable", str(tmp_path / "QSL73.exe")):
            result = resolve_doc_html("LIESMICH.html")
        assert result == html

    def test_returns_none_when_file_missing(self, tmp_path):
        with patch("sys.executable", str(tmp_path / "QSL73.exe")):
            result = resolve_doc_html("LIESMICH.html")
        assert result is None

    def test_returns_none_for_aenderungen_when_missing(self, tmp_path):
        with patch("sys.executable", str(tmp_path / "QSL73.exe")):
            result = resolve_doc_html("AENDERUNGEN.html")
        assert result is None

    def test_finds_aenderungen_when_present(self, tmp_path):
        html = tmp_path / "AENDERUNGEN.html"
        html.write_text("<html/>", encoding="utf-8")
        with patch("sys.executable", str(tmp_path / "QSL73.exe")):
            result = resolve_doc_html("AENDERUNGEN.html")
        assert result == html

    def test_looks_next_to_executable(self, tmp_path):
        sub = tmp_path / "app"
        sub.mkdir()
        html = sub / "LIESMICH.html"
        html.write_text("<html/>", encoding="utf-8")
        with patch("sys.executable", str(sub / "QSL73.exe")):
            result = resolve_doc_html("LIESMICH.html")
        assert result == html


class TestGetFallbackUrl:
    def test_liesmich_has_fallback(self):
        url = get_fallback_url("LIESMICH.html")
        assert url is not None
        assert "github.com" in url

    def test_aenderungen_has_fallback(self):
        url = get_fallback_url("AENDERUNGEN.html")
        assert url is not None
        assert "github.com" in url

    def test_unknown_file_returns_none(self):
        assert get_fallback_url("NONEXISTENT.html") is None
