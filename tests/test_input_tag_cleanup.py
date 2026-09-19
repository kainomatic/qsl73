# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
"""Tests für src/qsl73/input_tag_cleanup.py (Issue #41)."""
from unittest.mock import MagicMock

from qsl73.config import TagsConfig


def _make_config():
    return TagsConfig(input="qsl-card", confirmed="qsl-bestätigt", ignored="qsl-ignoriert")


class TestCountInputTagLeftovers:
    def test_sums_confirmed_and_ignored_counts(self):
        from qsl73.input_tag_cleanup import count_input_tag_leftovers

        client = MagicMock()
        client.count_documents_with_all_tags.side_effect = [2, 3]
        cfg = _make_config()

        n = count_input_tag_leftovers(client, cfg)

        assert n == 5
        client.count_documents_with_all_tags.assert_any_call(["qsl-card", "qsl-bestätigt"])
        client.count_documents_with_all_tags.assert_any_call(["qsl-card", "qsl-ignoriert"])

    def test_zero_when_nothing_found(self):
        from qsl73.input_tag_cleanup import count_input_tag_leftovers

        client = MagicMock()
        client.count_documents_with_all_tags.return_value = 0
        cfg = _make_config()

        assert count_input_tag_leftovers(client, cfg) == 0

    def test_propagates_network_error(self):
        """Netzwerkfehler wird NICHT verschluckt — der Aufrufer entscheidet über Retry."""
        from qsl73.input_tag_cleanup import count_input_tag_leftovers

        client = MagicMock()
        client.count_documents_with_all_tags.side_effect = RuntimeError("boom")
        cfg = _make_config()

        try:
            count_input_tag_leftovers(client, cfg)
            assert False, "hätte werfen müssen"
        except RuntimeError:
            pass


class TestFindInputTagLeftoverDocIds:
    def test_dedupes_docs_in_both_groups(self):
        from qsl73.input_tag_cleanup import find_input_tag_leftover_doc_ids

        client = MagicMock()
        client.list_documents_with_all_tags.side_effect = [
            [{"id": 1}, {"id": 2}],  # input+confirmed
            [{"id": 2}, {"id": 3}],  # input+ignored (id=2 doppelt)
        ]
        cfg = _make_config()

        ids = find_input_tag_leftover_doc_ids(client, cfg)

        assert ids == [1, 2, 3]

    def test_empty_when_no_docs(self):
        from qsl73.input_tag_cleanup import find_input_tag_leftover_doc_ids

        client = MagicMock()
        client.list_documents_with_all_tags.return_value = []
        cfg = _make_config()

        assert find_input_tag_leftover_doc_ids(client, cfg) == []


class TestRemoveInputTagFromLeftovers:
    def test_removes_only_input_tag_per_document(self):
        from qsl73.input_tag_cleanup import remove_input_tag_from_leftovers

        client = MagicMock()
        client.list_documents_with_all_tags.side_effect = [
            [{"id": 1}],
            [{"id": 2}],
        ]
        cfg = _make_config()

        remove_input_tag_from_leftovers(client, cfg, log_dir=MagicMock())

        assert client.remove_tag_from_document.call_count == 2
        client.remove_tag_from_document.assert_any_call(1, "qsl-card")
        client.remove_tag_from_document.assert_any_call(2, "qsl-card")
        client.set_document_tags.assert_not_called()

    def test_partial_failure_does_not_abort_rest(self, tmp_path):
        """Fehler bei einem Dokument bricht die übrigen nicht ab (Issue #41)."""
        from qsl73.input_tag_cleanup import remove_input_tag_from_leftovers

        client = MagicMock()
        client.list_documents_with_all_tags.side_effect = [
            [{"id": 1}, {"id": 2}],
            [],
        ]
        client.remove_tag_from_document.side_effect = [RuntimeError("boom"), None]
        cfg = _make_config()

        result = remove_input_tag_from_leftovers(client, cfg, log_dir=tmp_path)

        assert result.removed == 1
        assert result.failed == 1
        assert client.remove_tag_from_document.call_count == 2

    def test_writes_audit_summary_line(self, tmp_path):
        from qsl73.input_tag_cleanup import remove_input_tag_from_leftovers

        client = MagicMock()
        client.list_documents_with_all_tags.side_effect = [[{"id": 1}], []]
        cfg = _make_config()

        remove_input_tag_from_leftovers(client, cfg, log_dir=tmp_path)

        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "aktion=eingangs_tag_aufraeumen" in content
        assert "entfernt=1" in content
        assert "fehler=0" in content

    def test_no_docs_returns_zero_result_no_audit_error(self, tmp_path):
        from qsl73.input_tag_cleanup import remove_input_tag_from_leftovers

        client = MagicMock()
        client.list_documents_with_all_tags.return_value = []
        cfg = _make_config()

        result = remove_input_tag_from_leftovers(client, cfg, log_dir=tmp_path)

        assert result.removed == 0
        assert result.failed == 0
        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "entfernt=0" in content
