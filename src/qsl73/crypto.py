# QSL73 — Copyright (C) 2026 DF1DS (kainomatic) — SPDX-License-Identifier: GPL-3.0-or-later
import base64
import sys
from abc import ABC, abstractmethod


class CryptoUnavailableError(RuntimeError):
    """Wird ausgelöst wenn die geforderte Verschlüsselung nicht verfügbar ist.
    Auf Windows: DPAPI/pywin32 fehlt im Build.
    """


class CryptoBackend(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Verschlüsselt Klartext; gibt Base64-kodierten Geheimtext zurück."""

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Entschlüsselt Base64-kodierten Geheimtext; gibt Klartext zurück."""


class NullBackend(CryptoBackend):
    """UNSICHER — NUR für Tests und CI (Linux). Kein echter Schutz: nur Base64-Kodierung.
    Darf auf produktiven Windows-Systemen NICHT als Token-Speicher eingesetzt werden.
    """

    def encrypt(self, plaintext: str) -> str:
        return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        return base64.b64decode(ciphertext.encode("ascii")).decode("utf-8")


class DpapiBackend(CryptoBackend):
    """Windows DPAPI-Backend (nutzerkontext-gebunden). Benötigt pywin32.
    win32crypt wird lazy importiert — Modulimport schlägt auf Linux nicht fehl.
    """

    def encrypt(self, plaintext: str) -> str:
        import win32crypt  # noqa: PLC0415
        encrypted = win32crypt.CryptProtectData(
            plaintext.encode("utf-8"), None, None, None, None, 0
        )
        return base64.b64encode(encrypted).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        import win32crypt  # noqa: PLC0415
        data = base64.b64decode(ciphertext.encode("ascii"))
        _, plainbytes = win32crypt.CryptUnprotectData(data, None, None, None, 0)
        return plainbytes.decode("utf-8")


def get_default_backend() -> CryptoBackend:
    """Gibt das Standard-Crypto-Backend für diese Plattform zurück.

    Auf Windows: DpapiBackend (DPAPI, nutzerkontext-gebunden).
    Fehlt pywin32 auf Windows, wird CryptoUnavailableError geworfen — KEIN Fallback
    auf NullBackend (fail closed, nicht fail open).

    Auf anderen Plattformen (Linux/CI): NullBackend (nur Base64, kein echter Schutz;
    dort ist DPAPI nicht verfügbar und NullBackend ist für CI/Test akzeptiert).
    """
    if sys.platform == "win32":
        try:
            import win32crypt  # noqa: F401, PLC0415
        except ImportError:
            raise CryptoUnavailableError(
                "Sichere Token-Speicherung nicht verfügbar: pywin32/DPAPI fehlt. "
                "Bitte pywin32 installieren (pip install pywin32) oder den "
                "QSL73-Installer erneut ausführen."
            )
        return DpapiBackend()
    return NullBackend()
