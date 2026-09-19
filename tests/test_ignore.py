"""Tests für src/qsl73/ignore.py (ADR-0059)."""
from unittest.mock import MagicMock

import pytest


def _make_config(ignored="qsl-ignoriert", input_="qsl-card"):
    from qsl73.config import TagsConfig
    return TagsConfig(input=input_, confirmed="qsl-bestätigt", ignored=ignored)


class TestIgnoreCard:
    def test_sets_tag_and_writes_audit(self, tmp_path):
        from qsl73.ignore import ignore_card

        client = MagicMock()
        client.get_tag_id.return_value = 5
        cfg = _make_config()

        ignore_card(client, doc_id=42, tags_config=cfg, log_dir=tmp_path, callsign="DK1AB")

        client.replace_tags_on_document.assert_called_once_with(
            42, add_tag_names=["qsl-ignoriert"], remove_tag_names=["qsl-card"]
        )
        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "doc_id=42" in content
        assert "call=DK1AB" in content
        assert "aktion=ignoriert" in content

    def test_missing_callsign_defaults_to_placeholder(self, tmp_path):
        from qsl73.ignore import ignore_card

        client = MagicMock()
        client.get_tag_id.return_value = 5
        cfg = _make_config()

        ignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "call=?" in content

    def test_empty_tag_name_raises_without_side_effects(self, tmp_path):
        from qsl73.ignore import IgnoreTagMissingError, ignore_card

        client = MagicMock()
        cfg = _make_config(ignored="")

        with pytest.raises(IgnoreTagMissingError):
            ignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        client.create_tag.assert_not_called()
        client.replace_tags_on_document.assert_not_called()
        client.set_document_tags.assert_not_called()
        assert not (tmp_path / "audit.log").exists()

    def test_tag_not_in_paperless_raises_without_side_effects(self, tmp_path):
        from qsl73.ignore import IgnoreTagMissingError, ignore_card

        client = MagicMock()
        client.get_tag_id.return_value = None  # Tag existiert nicht in Paperless
        cfg = _make_config()

        with pytest.raises(IgnoreTagMissingError):
            ignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        client.create_tag.assert_not_called()
        client.replace_tags_on_document.assert_not_called()
        assert not (tmp_path / "audit.log").exists()

    def test_other_tags_untouched(self, tmp_path):
        """ignore_card ruft replace_tags_on_document EINMAL auf (EIN PATCH, kein halber Zustand)."""
        from qsl73.ignore import ignore_card

        client = MagicMock()
        client.get_tag_id.return_value = 5
        cfg = _make_config()

        ignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        # replace_tags_on_document (nicht set_document_tags direkt) — bestehende Tags
        # bleiben, siehe paperless.PaperlessClient.replace_tags_on_document.
        client.set_document_tags.assert_not_called()
        client.replace_tags_on_document.assert_called_once()


class TestUnignoreCard:
    def test_removes_tag_and_writes_audit(self, tmp_path):
        from qsl73.ignore import unignore_card

        client = MagicMock()
        client.get_tag_id.return_value = 5
        cfg = _make_config()

        unignore_card(client, doc_id=42, tags_config=cfg, log_dir=tmp_path, callsign="DK1AB")

        client.replace_tags_on_document.assert_called_once_with(
            42, add_tag_names=["qsl-card"], remove_tag_names=["qsl-ignoriert"]
        )
        content = (tmp_path / "audit.log").read_text(encoding="utf-8")
        assert "doc_id=42" in content
        assert "aktion=wieder_aufgenommen" in content

    def test_only_ignored_tag_removed(self, tmp_path):
        from qsl73.ignore import unignore_card

        client = MagicMock()
        client.get_tag_id.return_value = 5
        cfg = _make_config()

        unignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        client.set_document_tags.assert_not_called()
        client.replace_tags_on_document.assert_called_once()

    def test_empty_tag_name_raises_without_side_effects(self, tmp_path):
        from qsl73.ignore import IgnoreTagMissingError, unignore_card

        client = MagicMock()
        cfg = _make_config(ignored="")

        with pytest.raises(IgnoreTagMissingError):
            unignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        client.replace_tags_on_document.assert_not_called()
        assert not (tmp_path / "audit.log").exists()

    def test_tag_not_in_paperless_raises_without_side_effects(self, tmp_path):
        from qsl73.ignore import IgnoreTagMissingError, unignore_card

        client = MagicMock()
        client.get_tag_id.return_value = None
        cfg = _make_config()

        with pytest.raises(IgnoreTagMissingError):
            unignore_card(client, doc_id=1, tags_config=cfg, log_dir=tmp_path)

        client.replace_tags_on_document.assert_not_called()
        assert not (tmp_path / "audit.log").exists()
