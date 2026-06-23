# src/qsl73/gui/pdf_cache.py
"""RAM-Byte-Cache für PDF-Dokumente mit LRU-Verdrängung und Prefetch-Threads.

Gecacht werden rohe PDF-Bytes (doc_id → bytes). Keine Temp-Dateien (ADR-0050).
Rendering aus den Bytes geschieht on-demand in manual_assignment.py.

Öffentliche API:
  PdfByteCache  — LRU-Cache mit MB-Grenze, Prefetch-Threads, stop/clear
  PREFETCH_DEPTH — wie viele kommende Karten vorausgeladen werden
  CACHE_MAX_MB   — Gesamt-RAM-Obergrenze in MB
"""
from __future__ import annotations

import logging
import threading
from collections import OrderedDict
from typing import Callable

_log = logging.getLogger("qsl73")

# Zwei getrennte, benannte Stellschrauben (Issue #30 Kommentar 2 §2):
# - PREFETCH_DEPTH: Wartegefühl beim Vorwärtsklicken — 4 hält 4 Karten
#   im Netzwerk-Pipeline, ohne übermäßig viel Bandbreite im Voraus zu nutzen.
# - CACHE_MAX_MB: hält den RAM bei ~150 MB auch bei großen PDFs berechenbar gedeckelt;
#   MB-Grenze statt Stückzahl, weil PDF-Größen stark variieren (ADR-0051).
PREFETCH_DEPTH: int = 4
CACHE_MAX_MB: int = 150

# Finding 4: Konstante einmal ausrechnen statt in jedem _put()-Aufruf
_CACHE_MAX_BYTES: int = CACHE_MAX_MB * 1024 * 1024


class PdfByteCache:
    """LRU-Byte-Cache für PDF-Dokumente mit Hintergrund-Prefetch.

    Thread-safe. Alles im RAM — keine Dateizugriffe (ADR-0050).
    Lebensdauer: MainWindow (erstellt in __init__, gestoppt in _on_close).
    """

    def __init__(self) -> None:
        self._cache: OrderedDict[int, bytes] = OrderedDict()
        self._cache_bytes: int = 0
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        # Finding 1: Thread-Referenzen speichern für join() in stop()
        self._threads: list[threading.Thread] = []

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def get_or_download(self, doc_id: int, downloader: Callable[[int], bytes]) -> bytes:
        """Gibt PDF-Bytes aus Cache oder lädt sie via downloader (blockierend).

        Bei Cache-Treffer: kein Netzwerk. Bei Cache-Miss: download + in Cache legen.
        Thread-safe. Finding 2: Doppelt-Check nach Download vermeidet TOCTOU-Doppeldownload.
        """
        with self._lock:
            if doc_id in self._cache:
                self._cache.move_to_end(doc_id)
                return self._cache[doc_id]

        # Download ohne Lock (langsam, kein Blockieren anderer Threads)
        data = downloader(doc_id)

        with self._lock:
            # Doppelt-Check: Parallelthread könnte inzwischen eingelegt haben
            if doc_id not in self._cache:
                self._put_locked(doc_id, data)
            else:
                self._cache.move_to_end(doc_id)
            return self._cache[doc_id]

    def prefetch(self, doc_ids: list[int], downloader: Callable[[int], bytes]) -> None:
        """Lädt die ersten PREFETCH_DEPTH Einträge aus doc_ids im Hintergrund.

        Bereits gecachte IDs werden übersprungen. stop() wurde noch nicht aufgerufen
        ist Voraussetzung — nach stop() ist prefetch() ein No-op.
        """
        if self._stop_event.is_set():
            return
        for doc_id in doc_ids[:PREFETCH_DEPTH]:
            with self._lock:
                if doc_id in self._cache:
                    continue
                # Finding 1: stop-Check und Thread-Registrierung unter Lock
                if self._stop_event.is_set():
                    break
                t = threading.Thread(
                    target=self._prefetch_one,
                    args=(doc_id, downloader),
                    daemon=True,
                    name=f"pdf-prefetch-{doc_id}",
                )
                t.start()
                self._threads.append(t)

    def stop(self) -> None:
        """Signalisiert laufenden Prefetch-Threads zu stoppen und wartet auf sie (max. 2 s je Thread). Idempotent."""
        self._stop_event.set()
        # Finding 1: Threads joinen damit stop() wirklich blockiert bis alle fertig
        with self._lock:
            threads = list(self._threads)
            self._threads.clear()
        for t in threads:
            t.join(timeout=2.0)

    def clear(self) -> None:
        """Leert den Cache und setzt den Byte-Zähler zurück."""
        with self._lock:
            self._cache.clear()
            self._cache_bytes = 0

    def is_cached(self, doc_id: int) -> bool:
        """True wenn doc_id im Cache liegt (für Tests und Prefetch-Prüfung)."""
        with self._lock:
            return doc_id in self._cache

    def cache_size_bytes(self) -> int:
        """Aktuelle Gesamtgröße aller gecachten Bytes."""
        with self._lock:
            return self._cache_bytes

    # ------------------------------------------------------------------
    # Interne Helfer
    # ------------------------------------------------------------------

    def _put_locked(self, doc_id: int, data: bytes) -> None:
        """Legt data unter doc_id in den Cache (muss bereits unter self._lock aufgerufen werden).

        Verdrängt LRU-Einträge bis unter _CACHE_MAX_BYTES. Finding 4: Konstante statt
        inline-Berechnung.
        """
        if doc_id in self._cache:
            self._cache_bytes -= len(self._cache.pop(doc_id))
        self._cache[doc_id] = data
        self._cache.move_to_end(doc_id)
        self._cache_bytes += len(data)
        while self._cache_bytes > _CACHE_MAX_BYTES and self._cache:
            _, evicted = self._cache.popitem(last=False)
            self._cache_bytes -= len(evicted)

    def _put(self, doc_id: int, data: bytes) -> None:
        """Legt data unter doc_id in den Cache (erwirbt selbst den Lock)."""
        with self._lock:
            self._put_locked(doc_id, data)

    def _prefetch_one(self, doc_id: int, downloader: Callable[[int], bytes]) -> None:
        """Lädt ein Dokument im Hintergrund-Thread. Kein Absturz bei Fehlern."""
        if self._stop_event.is_set():
            return
        try:
            data = downloader(doc_id)
            if not self._stop_event.is_set():
                self._put(doc_id, data)
                _log.debug("pdf_cache: prefetch doc_id=%d (%d bytes)", doc_id, len(data))
        except Exception as exc:
            _log.debug("pdf_cache: prefetch fehlgeschlagen doc_id=%d: %s", doc_id, exc)
