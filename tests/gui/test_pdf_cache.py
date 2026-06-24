# tests/gui/test_pdf_cache.py
"""Tests für gui/pdf_cache.py — LRU-Byte-Cache + Prefetch-Threads.

Alle Tests sind tk-frei und laufen in CI ohne Display.
"""
import threading
import time
from unittest.mock import MagicMock

import pytest

from qsl73.gui.pdf_cache import CACHE_MAX_MB, PREFETCH_DEPTH, PdfByteCache


def _make_downloader(data_by_id: dict) -> MagicMock:
    """Mock-Downloader: gibt data_by_id[doc_id] zurück, zählt Aufrufe."""
    m = MagicMock(side_effect=lambda doc_id: data_by_id[doc_id])
    return m


def test_cache_miss_calls_downloader():
    """Cache-Miss: Downloader wird aufgerufen, bytes zurückgegeben."""
    cache = PdfByteCache()
    dl = _make_downloader({1: b"PDF-1"})

    result = cache.get_or_download(1, dl)

    assert result == b"PDF-1"
    dl.assert_called_once_with(1)
    cache.stop()


def test_cache_hit_no_download():
    """Cache-Treffer: zweiter Aufruf nutzt Cache — Downloader nur einmal."""
    cache = PdfByteCache()
    dl = _make_downloader({1: b"PDF-1"})

    cache.get_or_download(1, dl)
    result = cache.get_or_download(1, dl)

    assert result == b"PDF-1"
    assert dl.call_count == 1  # Kernbedingung: kein zweiter Download
    cache.stop()


def test_is_cached_after_get():
    """Nach get_or_download ist doc_id als gecacht markiert."""
    cache = PdfByteCache()
    dl = _make_downloader({5: b"DATA"})

    assert not cache.is_cached(5)
    cache.get_or_download(5, dl)
    assert cache.is_cached(5)
    cache.stop()


def test_lru_evicts_oldest_when_over_mb_limit():
    """LRU-Verdrängung: älteste Einträge rausfliegen wenn MB-Grenze überschritten."""
    cache = PdfByteCache()

    # Fülle den Cache bis fast zur Grenze
    max_bytes = CACHE_MAX_MB * 1024 * 1024
    chunk = b"X" * (max_bytes // 4)  # 4 Chunks = volle Grenze

    for i in range(4):
        dl = _make_downloader({i: chunk})
        cache.get_or_download(i, dl)

    # Alle 4 noch gecacht
    for i in range(4):
        assert cache.is_cached(i)

    # Einen weiteren Chunk hinzufügen → doc_id 0 (LRU) wird verdrängt
    dl_new = _make_downloader({99: chunk})
    cache.get_or_download(99, dl_new)

    assert not cache.is_cached(0), "Ältester Eintrag muss verdrängt worden sein"
    assert cache.is_cached(99)
    assert cache.cache_size_bytes() <= max_bytes
    cache.stop()


def test_cache_size_bytes_tracks_correctly():
    """cache_size_bytes steigt beim Einfügen und sinkt beim Verdrängen."""
    cache = PdfByteCache()
    dl = _make_downloader({1: b"A" * 100, 2: b"B" * 200})

    cache.get_or_download(1, dl)
    assert cache.cache_size_bytes() == 100

    cache.get_or_download(2, dl)
    assert cache.cache_size_bytes() == 300
    cache.stop()


def test_prefetch_loads_bytes_in_background():
    """Prefetch lädt Bytes im Hintergrund — nachfolgender get ist Cache-Treffer."""
    cache = PdfByteCache()
    event = threading.Event()

    def slow_dl(doc_id):
        event.wait(timeout=2.0)
        return b"PREFETCHED"

    dl = MagicMock(side_effect=slow_dl)

    cache.prefetch([42], dl)
    event.set()  # Downloader freischalten

    # Warten bis Prefetch abgeschlossen (max. 2 s)
    deadline = time.monotonic() + 2.0
    while not cache.is_cached(42) and time.monotonic() < deadline:
        time.sleep(0.05)

    assert cache.is_cached(42), "Prefetch muss 42 in Cache geladen haben"
    dl.assert_called_once_with(42)
    cache.stop()


def test_stop_prevents_new_prefetch_work():
    """Nach stop() wird kein neues Download mehr ausgeführt."""
    cache = PdfByteCache()
    downloaded = []

    def slow_dl(doc_id):
        time.sleep(0.5)  # lang genug damit stop() vorher greift
        downloaded.append(doc_id)
        return b"DATA"

    cache.stop()  # sofort stoppen
    cache.prefetch([1, 2, 3], slow_dl)  # startet keine Threads mehr nach stop

    time.sleep(0.2)
    # Finding 3: Assertion hinzufügen — nach stop() darf kein neuer Download laufen
    assert downloaded == [], f"Prefetch lief nach stop() noch: {downloaded}"
    cache.stop()  # zweimaliges stop() muss safe sein


def test_backward_navigation_cache_hit():
    """Zurückblättern auf geladene Karte: kein erneuter Download."""
    cache = PdfByteCache()
    dl = _make_downloader({10: b"PDF-10", 11: b"PDF-11"})

    # Karte 10 laden (vorwärts)
    cache.get_or_download(10, dl)
    # Karte 11 laden (vorwärts)
    cache.get_or_download(11, dl)
    # Zurück zu Karte 10 (Rückwärts)
    result = cache.get_or_download(10, dl)

    assert result == b"PDF-10"
    assert dl.call_count == 2  # 10 + 11, nicht ein drittes Mal
    cache.stop()


def test_no_temp_files_created(tmp_path, monkeypatch):
    """Cache erzeugt keine Temp-Dateien — alles im RAM."""
    import tempfile

    created_files = []
    original_mktemp = tempfile.mkstemp

    def recording_mkstemp(*args, **kwargs):
        result = original_mktemp(*args, **kwargs)
        created_files.append(result)
        return result

    monkeypatch.setattr(tempfile, "mkstemp", recording_mkstemp)

    cache = PdfByteCache()
    dl = _make_downloader({1: b"PDF-DATA"})
    cache.get_or_download(1, dl)
    cache.stop()

    assert created_files == [], "Cache darf keine Temp-Dateien erzeugen"


def test_clear_empties_cache():
    """clear() leert Cache — nachfolgender get muss neu downloaden."""
    cache = PdfByteCache()
    dl = _make_downloader({1: b"PDF-1"})

    cache.get_or_download(1, dl)
    assert cache.is_cached(1)

    cache.clear()
    assert not cache.is_cached(1)
    assert cache.cache_size_bytes() == 0

    # Nochmaliger Download nach clear
    cache.get_or_download(1, dl)
    assert dl.call_count == 2
    cache.stop()


def test_constants_have_sensible_values():
    """Benannte Konstanten existieren und haben sinnvolle Werte."""
    assert PREFETCH_DEPTH >= 1
    assert CACHE_MAX_MB >= 50
