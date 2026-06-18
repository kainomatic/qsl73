# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
import logging

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # Sekunden


# ── Exceptions ────────────────────────────────────────────────────────────────


class PaperlessError(Exception):
    """Basisklasse für alle Paperless-Fehler."""


class PaperlessConnectionError(PaperlessError):
    """Server nicht erreichbar oder Zeitüberschreitung."""


class PaperlessAuthError(PaperlessError):
    """Authentifizierung fehlgeschlagen (HTTP 401/403)."""


class PaperlessNotFoundError(PaperlessError):
    """Ressource nicht gefunden (HTTP 404)."""


class PaperlessAPIError(PaperlessError):
    """Sonstiger API-Fehler (z. B. HTTP 5xx)."""


# ── interne Hilfsfunktion ────────────────────────────────────────────────────


def _raise_for_status(resp: requests.Response) -> None:
    """Wandelt HTTP-Fehlercodes in sprechende Exceptions um.
    Keine Secrets (Token, Passwort) in Fehlertexten.
    """
    code = resp.status_code
    if code < 400:
        return
    if code in (401, 403):
        raise PaperlessAuthError(
            f"Paperless: Zugriff verweigert (HTTP {code}). "
            "Token prüfen oder im Setup-Assistenten erneuern."
        )
    if code == 404:
        raise PaperlessNotFoundError(
            f"Paperless: Ressource nicht gefunden (HTTP 404)."
        )
    raise PaperlessAPIError(f"Paperless: API-Fehler (HTTP {code}).")


# ── Client ────────────────────────────────────────────────────────────────────


class PaperlessClient:
    """HTTP-Client für die Paperless-ngx REST-API."""

    def __init__(self, base_url: str, token: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._base = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Token {token}",
            "Accept": "application/json",
        })

    @classmethod
    def from_password(
        cls,
        base_url: str,
        username: str,
        password: str,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> tuple["PaperlessClient", str]:
        """Tauscht Benutzername/Passwort gegen Token (POST /api/token/).

        Passwort wird NICHT gespeichert. Gibt (Client, Token-Klartext) zurück.
        Der Aufrufer übergibt den Token an die Config-Schicht zur DPAPI-Verschlüsselung.
        """
        url = base_url.rstrip("/") + "/api/token/"
        try:
            resp = requests.post(
                url,
                json={"username": username, "password": password},
                timeout=timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessConnectionError(
                f"Paperless-Server nicht erreichbar ({base_url.rstrip('/')})."
            ) from exc
        except requests.exceptions.Timeout:
            raise PaperlessConnectionError(
                f"Zeitüberschreitung beim Verbinden mit Paperless ({base_url.rstrip('/')})."
            )

        if resp.status_code == 400:
            raise PaperlessAuthError(
                "Authentifizierung fehlgeschlagen: Benutzername oder Passwort falsch."
            )
        _raise_for_status(resp)

        token = resp.json().get("token", "")
        if not token:
            raise PaperlessAPIError("Paperless hat keinen Token zurückgeliefert.")
        return cls(base_url, token, timeout=timeout), token

    # ── Dokument-Abfragen ────────────────────────────────────────────────

    def get_documents_by_tag(
        self,
        tag_name: str,
        exclude_tag_name: str | None = None,
    ) -> list[dict]:
        """Gibt alle Dokumente mit dem angegebenen Tag zurück.

        exclude_tag_name: Wenn gesetzt, werden Dokumente mit diesem Tag serverseitig
        ausgeschlossen (tags__id__none). Existiert der Ausschluss-Tag nicht in Paperless,
        wird kein Ausschluss angewendet. Paginierung vollständig aufgelöst.
        """
        base_query = f"{self._base}/api/documents/?tags__name__iexact={tag_name}"
        if exclude_tag_name is not None:
            exclude_id = self.get_tag_id(exclude_tag_name)
            if exclude_id is not None:
                base_query += f"&tags__id__none={exclude_id}"
        url: str | None = base_query
        results: list[dict] = []
        while url:
            data = self._get_json(url)
            results.extend(data.get("results", []))
            url = data.get("next")
        return results

    def get_document_content(self, doc_id: int) -> str:
        """Gibt den OCR-Text eines Dokuments zurück (GET /api/documents/{id}/?fields=content)."""
        data = self._get_json(f"{self._base}/api/documents/{doc_id}/?fields=content")
        return data.get("content", "")

    def get_document_preview(self, doc_id: int) -> bytes:
        """Gibt den Inline-Preview (PDF) als Bytes zurück."""
        return self._get_binary(f"{self._base}/api/documents/{doc_id}/preview/")

    def get_document_download(self, doc_id: int) -> bytes:
        """Gibt die Original-Datei als Bytes zurück (höchste Auflösung)."""
        return self._get_binary(f"{self._base}/api/documents/{doc_id}/download/")

    def get_document_thumb(self, doc_id: int) -> bytes:
        """Gibt das Thumbnail als Bytes zurück."""
        return self._get_binary(f"{self._base}/api/documents/{doc_id}/thumb/")

    # ── Tag-Operationen ──────────────────────────────────────────────────

    def get_tag_id(self, tag_name: str) -> int | None:
        """Gibt die Paperless-Tag-ID für einen Tag-Namen zurück, oder None."""
        url: str | None = f"{self._base}/api/tags/?name__iexact={tag_name}"
        while url:
            data = self._get_json(url)
            for tag in data.get("results", []):
                if tag.get("name", "").lower() == tag_name.lower():
                    return int(tag["id"])
            url = data.get("next")
        return None

    def list_tags(self) -> list[dict]:
        """Gibt alle Tags zurück (mind. id, name, matching_algorithm). Paginierung vollständig aufgelöst."""
        url: str | None = f"{self._base}/api/tags/"
        results: list[dict] = []
        while url:
            data = self._get_json(url)
            results.extend(data.get("results", []))
            url = data.get("next")
        return results

    def create_tag(
        self,
        name: str,
        *,
        matching_algorithm: int = 0,
        is_inbox_tag: bool = False,
    ) -> int:
        """Legt einen Tag an (POST /api/tags/). Gibt ID zurück.

        Existiert bereits ein Tag mit dem Namen (case-insensitive), wird KEIN
        Duplikat angelegt — die vorhandene ID wird zurückgegeben.
        """
        existing_id = self.get_tag_id(name)
        if existing_id is not None:
            return existing_id
        url = f"{self._base}/api/tags/"
        payload = {
            "name": name,
            "matching_algorithm": matching_algorithm,
            "match": "",
            "is_inbox_tag": is_inbox_tag,
        }
        try:
            resp = self._session.post(url, json=payload, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessConnectionError(
                "Paperless-Server nicht erreichbar (Tag anlegen)."
            ) from exc
        except requests.exceptions.Timeout:
            raise PaperlessConnectionError(
                "Zeitüberschreitung beim Anlegen des Tags."
            )
        _raise_for_status(resp)
        return int(resp.json()["id"])

    def set_document_tags(self, doc_id: int, tag_ids: list[int]) -> None:
        """Ersetzt die Tag-Liste eines Dokuments vollständig (PATCH)."""
        url = f"{self._base}/api/documents/{doc_id}/"
        try:
            resp = self._session.patch(url, json={"tags": tag_ids}, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessConnectionError(
                f"Paperless-Server nicht erreichbar (Tags schreiben, Dok. {doc_id})."
            ) from exc
        except requests.exceptions.Timeout:
            raise PaperlessConnectionError(
                f"Zeitüberschreitung beim Schreiben der Tags (Dok. {doc_id})."
            )
        _raise_for_status(resp)

    def add_tag_to_document(self, doc_id: int, tag_name: str) -> None:
        """Fügt einen Tag einem Dokument hinzu. Bestehende Tags bleiben erhalten."""
        tag_id = self.get_tag_id(tag_name)
        if tag_id is None:
            raise PaperlessNotFoundError(
                f"Tag '{tag_name}' in Paperless nicht gefunden."
            )
        doc = self._get_json(f"{self._base}/api/documents/{doc_id}/?fields=tags")
        current_ids: list[int] = doc.get("tags", [])
        if tag_id not in current_ids:
            self.set_document_tags(doc_id, current_ids + [tag_id])

    def remove_tag_from_document(self, doc_id: int, tag_name: str) -> None:
        """Entfernt einen Tag von einem Dokument. Fehlendes Tag wird stillschweigend ignoriert."""
        tag_id = self.get_tag_id(tag_name)
        if tag_id is None:
            return
        doc = self._get_json(f"{self._base}/api/documents/{doc_id}/?fields=tags")
        current_ids: list[int] = doc.get("tags", [])
        updated = [t for t in current_ids if t != tag_id]
        if updated != current_ids:
            self.set_document_tags(doc_id, updated)

    # ── interne Hilfsmethoden ─────────────────────────────────────────────

    def _get_json(self, url: str) -> dict:
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessConnectionError(
                "Paperless-Server nicht erreichbar."
            ) from exc
        except requests.exceptions.Timeout:
            raise PaperlessConnectionError(
                "Zeitüberschreitung beim Abruf von Paperless."
            )
        _raise_for_status(resp)
        return resp.json()

    def _get_binary(self, url: str) -> bytes:
        try:
            resp = self._session.get(url, timeout=self._timeout)
        except requests.exceptions.ConnectionError as exc:
            raise PaperlessConnectionError(
                "Paperless-Server nicht erreichbar."
            ) from exc
        except requests.exceptions.Timeout:
            raise PaperlessConnectionError(
                "Zeitüberschreitung beim Datei-Download."
            )
        _raise_for_status(resp)
        return resp.content
