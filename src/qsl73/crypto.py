import base64
import sys
from abc import ABC, abstractmethod


class CryptoBackend(ABC):
    @abstractmethod
    def encrypt(self, plaintext: str) -> str:
        """Verschlüsselt Klartext; gibt Base64-kodierten Geheimtext zurück."""

    @abstractmethod
    def decrypt(self, ciphertext: str) -> str:
        """Entschlüsselt Base64-kodierten Geheimtext; gibt Klartext zurück."""


class NullBackend(CryptoBackend):
    """Base64-only, kein echter Schutz. Für Tests und Nicht-Windows-Umgebungen."""

    def encrypt(self, plaintext: str) -> str:
        return base64.b64encode(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        return base64.b64decode(ciphertext.encode("ascii")).decode("utf-8")


class DpapiBackend(CryptoBackend):
    """Windows DPAPI-Backend (nutzerkontext-gebunden). Benötigt pywin32.
    win32crypt wird lazy importiert — schlägt auf Linux nicht beim Modulimport fehl.
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
    """Gibt DpapiBackend auf Windows zurück, sonst NullBackend."""
    if sys.platform == "win32":
        return DpapiBackend()
    return NullBackend()
