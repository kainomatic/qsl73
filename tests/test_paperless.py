import json

import pytest
import responses as rsps

from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout

from qsl73.paperless import (
    PaperlessClient,
    PaperlessAuthError,
    PaperlessConnectionError,
    PaperlessNotFoundError,
    PaperlessAPIError,
)

BASE = "https://paperless.example.com"
TOKEN = "testtoken123"


@pytest.fixture
def client():
    return PaperlessClient(BASE, TOKEN)


# ── Auth ──────────────────────────────────────────────────────────────────────


class TestAuthToken:
    def test_authorization_header_set(self, client):
        assert client._session.headers["Authorization"] == f"Token {TOKEN}"

    @rsps.activate
    def test_from_password_exchanges_credentials(self):
        secret_token = "returned-secret-token"
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={"token": secret_token}, status=200)
        c, token = PaperlessClient.from_password(BASE, "user", "pw")
        assert token == secret_token
        assert c._session.headers["Authorization"] == f"Token {secret_token}"

    @rsps.activate
    def test_from_password_wrong_credentials_raises_auth_error(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={"detail": "Invalid"}, status=400)
        with pytest.raises(PaperlessAuthError):
            PaperlessClient.from_password(BASE, "user", "wrong")

    @rsps.activate
    def test_from_password_password_not_in_error_message(self):
        secret_pw = "do-not-leak-this-password"
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={}, status=400)
        try:
            PaperlessClient.from_password(BASE, "user", secret_pw)
        except PaperlessAuthError as exc:
            assert secret_pw not in str(exc)

    @rsps.activate
    def test_from_password_401_raises_auth_error(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={}, status=401)
        with pytest.raises(PaperlessAuthError):
            PaperlessClient.from_password(BASE, "user", "pw")

    @rsps.activate
    def test_from_password_server_error_raises_api_error(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={}, status=500)
        with pytest.raises(PaperlessAPIError):
            PaperlessClient.from_password(BASE, "user", "pw")

    @rsps.activate
    def test_from_password_connection_error(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", body=RequestsConnectionError("refused"))
        with pytest.raises(PaperlessConnectionError):
            PaperlessClient.from_password(BASE, "user", "pw")

    @rsps.activate
    def test_from_password_timeout(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", body=Timeout("timeout"))
        with pytest.raises(PaperlessConnectionError):
            PaperlessClient.from_password(BASE, "user", "pw")

    @rsps.activate
    def test_from_password_empty_token_raises(self):
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={"token": ""}, status=200)
        with pytest.raises(PaperlessAPIError, match="Token"):
            PaperlessClient.from_password(BASE, "user", "pw")


# ── Dokumente nach Tag ────────────────────────────────────────────────────────


class TestDocumentsByTag:
    @rsps.activate
    def test_single_page(self, client):
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [{"id": 1, "title": "Doc1"}, {"id": 2, "title": "Doc2"}],
            },
        )
        docs = client.get_documents_by_tag("qsl-card")
        assert len(docs) == 2
        assert docs[0]["id"] == 1
        assert docs[1]["id"] == 2

    @rsps.activate
    def test_pagination_collects_all_pages(self, client):
        page2_url = f"{BASE}/api/documents/?tags__name__iexact=qsl-card&page=2"
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={
                "count": 4,
                "next": page2_url,
                "previous": None,
                "results": [{"id": 1}, {"id": 2}],
            },
        )
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={
                "count": 4,
                "next": None,
                "previous": f"{BASE}/api/documents/?tags__name__iexact=qsl-card",
                "results": [{"id": 3}, {"id": 4}],
            },
        )
        docs = client.get_documents_by_tag("qsl-card")
        assert len(docs) == 4
        assert [d["id"] for d in docs] == [1, 2, 3, 4]

    @rsps.activate
    def test_three_pages_fully_collected(self, client):
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={"count": 6, "next": f"{BASE}/api/documents/?page=2", "previous": None,
                  "results": [{"id": 1}, {"id": 2}]},
        )
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={"count": 6, "next": f"{BASE}/api/documents/?page=3", "previous": None,
                  "results": [{"id": 3}, {"id": 4}]},
        )
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={"count": 6, "next": None, "previous": None,
                  "results": [{"id": 5}, {"id": 6}]},
        )
        docs = client.get_documents_by_tag("qsl-card")
        assert len(docs) == 6

    @rsps.activate
    def test_empty_result(self, client):
        rsps.add(
            rsps.GET,
            f"{BASE}/api/documents/",
            json={"count": 0, "next": None, "previous": None, "results": []},
        )
        assert client.get_documents_by_tag("nonexistent") == []

    @rsps.activate
    def test_connection_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/", body=RequestsConnectionError("refused"))
        with pytest.raises(PaperlessConnectionError):
            client.get_documents_by_tag("qsl-card")

    @rsps.activate
    def test_timeout(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/", body=Timeout())
        with pytest.raises(PaperlessConnectionError):
            client.get_documents_by_tag("qsl-card")

    @rsps.activate
    def test_401_raises_auth_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/", json={}, status=401)
        with pytest.raises(PaperlessAuthError):
            client.get_documents_by_tag("qsl-card")

    @rsps.activate
    def test_500_raises_api_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/", json={}, status=500)
        with pytest.raises(PaperlessAPIError):
            client.get_documents_by_tag("qsl-card")


# ── OCR-Text ──────────────────────────────────────────────────────────────────


class TestDocumentContent:
    @rsps.activate
    def test_returns_ocr_text(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/42/", json={"content": "Hello OCR"})
        assert client.get_document_content(42) == "Hello OCR"

    @rsps.activate
    def test_missing_content_field_returns_empty_string(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/42/", json={})
        assert client.get_document_content(42) == ""

    @rsps.activate
    def test_not_found_raises(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/999/", json={}, status=404)
        with pytest.raises(PaperlessNotFoundError):
            client.get_document_content(999)

    @rsps.activate
    def test_connection_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/", body=RequestsConnectionError())
        with pytest.raises(PaperlessConnectionError):
            client.get_document_content(1)

    @rsps.activate
    def test_timeout(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/", body=Timeout())
        with pytest.raises(PaperlessConnectionError):
            client.get_document_content(1)


# ── Bild-/Datei-Endpunkte ────────────────────────────────────────────────────


class TestBinaryEndpoints:
    @rsps.activate
    def test_get_preview_returns_bytes(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/preview/",
                 body=b"%PDF-preview", content_type="application/pdf")
        assert client.get_document_preview(1) == b"%PDF-preview"

    @rsps.activate
    def test_get_download_returns_bytes(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/download/",
                 body=b"%PDF-original", content_type="application/pdf")
        assert client.get_document_download(1) == b"%PDF-original"

    @rsps.activate
    def test_get_thumb_returns_bytes(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/thumb/",
                 body=b"\xff\xd8\xff\xe0", content_type="image/jpeg")
        assert client.get_document_thumb(1) == b"\xff\xd8\xff\xe0"

    @rsps.activate
    def test_preview_connection_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/preview/", body=RequestsConnectionError())
        with pytest.raises(PaperlessConnectionError):
            client.get_document_preview(1)

    @rsps.activate
    def test_preview_timeout(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/preview/", body=Timeout())
        with pytest.raises(PaperlessConnectionError):
            client.get_document_preview(1)

    @rsps.activate
    def test_download_not_found(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/99/download/", json={}, status=404)
        with pytest.raises(PaperlessNotFoundError):
            client.get_document_download(99)

    @rsps.activate
    def test_thumb_server_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/thumb/", json={}, status=503)
        with pytest.raises(PaperlessAPIError):
            client.get_document_thumb(1)


# ── Tag-Operationen ───────────────────────────────────────────────────────────


class TestTagOperations:
    @rsps.activate
    def test_get_tag_id_found(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 7, "name": "qsl-card"}]})
        assert client.get_tag_id("qsl-card") == 7

    @rsps.activate
    def test_get_tag_id_case_insensitive(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 7, "name": "QSL-Card"}]})
        assert client.get_tag_id("qsl-card") == 7

    @rsps.activate
    def test_get_tag_id_not_found_returns_none(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        assert client.get_tag_id("nonexistent") is None

    @rsps.activate
    def test_get_tag_id_paginated(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 2, "next": f"{BASE}/api/tags/?page=2",
                       "results": [{"id": 1, "name": "other"}]})
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 2, "next": None,
                       "results": [{"id": 9, "name": "qsl-card"}]})
        assert client.get_tag_id("qsl-card") == 9

    @rsps.activate
    def test_set_document_tags_sends_correct_body(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/",
                 json={"id": 5, "tags": [1, 2, 3]})
        client.set_document_tags(5, [1, 2, 3])
        body = json.loads(rsps.calls[0].request.body)
        assert body == {"tags": [1, 2, 3]}

    @rsps.activate
    def test_set_document_tags_empty_list(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/", json={"id": 5, "tags": []})
        client.set_document_tags(5, [])
        body = json.loads(rsps.calls[0].request.body)
        assert body == {"tags": []}

    @rsps.activate
    def test_add_tag_to_document(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "qsl-bestätigt"}]})
        rsps.add(rsps.GET, f"{BASE}/api/documents/5/", json={"tags": [1, 2]})
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/",
                 json={"id": 5, "tags": [1, 2, 9]})
        client.add_tag_to_document(5, "qsl-bestätigt")
        body = json.loads(rsps.calls[2].request.body)
        assert 9 in body["tags"]
        assert 1 in body["tags"]

    @rsps.activate
    def test_add_tag_already_present_no_patch(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "qsl-bestätigt"}]})
        rsps.add(rsps.GET, f"{BASE}/api/documents/5/", json={"tags": [1, 9]})
        client.add_tag_to_document(5, "qsl-bestätigt")
        assert len(rsps.calls) == 2  # kein PATCH

    @rsps.activate
    def test_add_tag_not_found_raises(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        with pytest.raises(PaperlessNotFoundError, match="qsl-bestätigt"):
            client.add_tag_to_document(5, "qsl-bestätigt")

    @rsps.activate
    def test_remove_tag_from_document(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "qsl-card"}]})
        rsps.add(rsps.GET, f"{BASE}/api/documents/5/", json={"tags": [1, 9, 2]})
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/",
                 json={"id": 5, "tags": [1, 2]})
        client.remove_tag_from_document(5, "qsl-card")
        body = json.loads(rsps.calls[2].request.body)
        assert 9 not in body["tags"]
        assert 1 in body["tags"]

    @rsps.activate
    def test_remove_tag_not_present_no_patch(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "qsl-card"}]})
        rsps.add(rsps.GET, f"{BASE}/api/documents/5/", json={"tags": [1, 2]})
        client.remove_tag_from_document(5, "qsl-card")
        assert len(rsps.calls) == 2  # kein PATCH

    @rsps.activate
    def test_remove_tag_nonexistent_in_paperless_is_noop(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        client.remove_tag_from_document(5, "phantom-tag")  # darf nicht werfen

    @rsps.activate
    def test_patch_server_error_raises(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/", json={}, status=500)
        with pytest.raises(PaperlessAPIError):
            client.set_document_tags(5, [1])

    @rsps.activate
    def test_patch_unauthorized_raises(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/", json={}, status=403)
        with pytest.raises(PaperlessAuthError):
            client.set_document_tags(5, [1])

    @rsps.activate
    def test_patch_connection_error(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/",
                 body=RequestsConnectionError())
        with pytest.raises(PaperlessConnectionError):
            client.set_document_tags(5, [1])

    @rsps.activate
    def test_patch_timeout(self, client):
        rsps.add(rsps.PATCH, f"{BASE}/api/documents/5/", body=Timeout())
        with pytest.raises(PaperlessConnectionError):
            client.set_document_tags(5, [1])


# ── Keine Secrets in Fehlermeldungen ─────────────────────────────────────────


class TestNoSecretsInErrors:
    @rsps.activate
    def test_token_not_in_connection_error(self):
        secret = "my-very-secret-api-token"
        c = PaperlessClient(BASE, secret)
        rsps.add(rsps.GET, f"{BASE}/api/documents/",
                 body=RequestsConnectionError("connection refused"))
        try:
            c.get_documents_by_tag("qsl-card")
        except PaperlessConnectionError as exc:
            assert secret not in str(exc)

    @rsps.activate
    def test_token_not_in_http_error(self):
        secret = "my-very-secret-api-token"
        c = PaperlessClient(BASE, secret)
        rsps.add(rsps.GET, f"{BASE}/api/documents/", json={}, status=500)
        try:
            c.get_documents_by_tag("qsl-card")
        except PaperlessAPIError as exc:
            assert secret not in str(exc)

    @rsps.activate
    def test_token_not_in_auth_error(self):
        secret = "my-very-secret-api-token"
        c = PaperlessClient(BASE, secret)
        rsps.add(rsps.GET, f"{BASE}/api/documents/", json={}, status=401)
        try:
            c.get_documents_by_tag("qsl-card")
        except PaperlessAuthError as exc:
            assert secret not in str(exc)

    @rsps.activate
    def test_password_not_in_auth_error(self):
        secret_pw = "do-not-leak-this-password"
        rsps.add(rsps.POST, f"{BASE}/api/token/", json={}, status=400)
        try:
            PaperlessClient.from_password(BASE, "user", secret_pw)
        except PaperlessAuthError as exc:
            assert secret_pw not in str(exc)

    @rsps.activate
    def test_password_not_in_connection_error(self):
        secret_pw = "do-not-leak-this-password"
        rsps.add(rsps.POST, f"{BASE}/api/token/",
                 body=RequestsConnectionError("refused"))
        try:
            PaperlessClient.from_password(BASE, "user", secret_pw)
        except PaperlessConnectionError as exc:
            assert secret_pw not in str(exc)


# ── Fehlercodes vollständig ───────────────────────────────────────────────────


class TestHttpErrorCodes:
    @pytest.mark.parametrize("status", [401, 403])
    @rsps.activate
    def test_auth_errors(self, client, status):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/", json={}, status=status)
        with pytest.raises(PaperlessAuthError):
            client.get_document_content(1)

    @rsps.activate
    def test_404_raises_not_found(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/", json={}, status=404)
        with pytest.raises(PaperlessNotFoundError):
            client.get_document_content(1)

    @pytest.mark.parametrize("status", [500, 502, 503])
    @rsps.activate
    def test_server_errors(self, client, status):
        rsps.add(rsps.GET, f"{BASE}/api/documents/1/", json={}, status=status)
        with pytest.raises(PaperlessAPIError):
            client.get_document_content(1)


# ── Tag-Auflistung ────────────────────────────────────────────────────────────


class TestListTags:
    @rsps.activate
    def test_list_tags_single_page(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 2, "next": None, "results": [
                     {"id": 1, "name": "qsl-card", "matching_algorithm": 0},
                     {"id": 2, "name": "qsl-bestätigt", "matching_algorithm": 0},
                 ]})
        tags = client.list_tags()
        assert len(tags) == 2
        assert tags[0]["id"] == 1
        assert tags[0]["name"] == "qsl-card"

    @rsps.activate
    def test_list_tags_includes_matching_algorithm(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None, "results": [
                     {"id": 5, "name": "auto-tag", "matching_algorithm": 6},
                 ]})
        tags = client.list_tags()
        assert tags[0]["matching_algorithm"] == 6

    @rsps.activate
    def test_list_tags_pagination_collects_all(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 3, "next": f"{BASE}/api/tags/?page=2",
                       "results": [{"id": 1, "name": "a", "matching_algorithm": 0}]})
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 3, "next": f"{BASE}/api/tags/?page=3",
                       "results": [{"id": 2, "name": "b", "matching_algorithm": 0}]})
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 3, "next": None,
                       "results": [{"id": 3, "name": "c", "matching_algorithm": 0}]})
        tags = client.list_tags()
        assert len(tags) == 3
        assert [t["id"] for t in tags] == [1, 2, 3]

    @rsps.activate
    def test_list_tags_empty(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        assert client.list_tags() == []

    @rsps.activate
    def test_list_tags_connection_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/", body=RequestsConnectionError())
        with pytest.raises(PaperlessConnectionError):
            client.list_tags()

    @rsps.activate
    def test_list_tags_auth_error(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/", json={}, status=401)
        with pytest.raises(PaperlessAuthError):
            client.list_tags()


# ── Tag anlegen ────────────────────────────────────────────────────────────


class TestCreateTag:
    @rsps.activate
    def test_create_tag_new_returns_id(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        rsps.add(rsps.POST, f"{BASE}/api/tags/",
                 json={"id": 42, "name": "qsl-neu", "matching_algorithm": 0},
                 status=201)
        tag_id = client.create_tag("qsl-neu")
        assert tag_id == 42

    @rsps.activate
    def test_create_tag_sends_matching_algorithm_zero(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        rsps.add(rsps.POST, f"{BASE}/api/tags/",
                 json={"id": 7, "name": "new-tag", "matching_algorithm": 0},
                 status=201)
        client.create_tag("new-tag")
        body = json.loads(rsps.calls[1].request.body)
        assert body["matching_algorithm"] == 0
        assert body["match"] == ""
        assert body["name"] == "new-tag"

    @rsps.activate
    def test_create_tag_existing_no_duplicate(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "qsl-bestätigt"}]})
        tag_id = client.create_tag("qsl-bestätigt")
        assert tag_id == 9
        assert all(c.request.method == "GET" for c in rsps.calls)

    @rsps.activate
    def test_create_tag_existing_case_insensitive_no_duplicate(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 1, "next": None,
                       "results": [{"id": 9, "name": "QSL-Bestätigt"}]})
        tag_id = client.create_tag("qsl-bestätigt")
        assert tag_id == 9
        assert all(c.request.method == "GET" for c in rsps.calls)

    @rsps.activate
    def test_create_tag_connection_error_on_post(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        rsps.add(rsps.POST, f"{BASE}/api/tags/", body=RequestsConnectionError())
        with pytest.raises(PaperlessConnectionError):
            client.create_tag("fail-tag")

    @rsps.activate
    def test_create_tag_api_error_on_post(self, client):
        rsps.add(rsps.GET, f"{BASE}/api/tags/",
                 json={"count": 0, "next": None, "results": []})
        rsps.add(rsps.POST, f"{BASE}/api/tags/", json={}, status=500)
        with pytest.raises(PaperlessAPIError):
            client.create_tag("fail-tag")
