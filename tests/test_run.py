# tests/test_run.py
"""Tests für run.py — Orchestrierung Sammeln→Auswerten→Matchen→Schreiben."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from qsl73.run import CardResult, RunResult


def test_card_result_fields():
    """CardResult ist instanziierbar mit den erwarteten Feldern."""
    from qsl73.matching import CardFields, MatchOutcome, MatchResult

    cr = CardResult(
        doc_id=42,
        card_fields=CardFields(None, None, None, None, None),
        source="none",
        outcome=MatchOutcome(MatchResult.NO_MATCH, None, []),
        existing_confirmations=[],
    )
    assert cr.doc_id == 42
    assert cr.source == "none"
    assert cr.existing_confirmations == []


def test_run_result_fields():
    """RunResult ist instanziierbar und trägt fingerprint + expected_states."""
    rr = RunResult(
        certain=[],
        uncertain=[],
        no_match=[],
        fingerprint={"main_mtime": 1.0, "main_size": 100},
        expected_states={"QSO1": "No"},
    )
    assert rr.certain == []
    assert rr.fingerprint["main_size"] == 100
    assert rr.expected_states["QSO1"] == "No"
