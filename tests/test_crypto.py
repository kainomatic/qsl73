import sys
import pytest
from qsl73.crypto import NullBackend, get_default_backend, CryptoUnavailableError


def _win32crypt_available() -> bool:
    try:
        import win32crypt  # noqa: F401
        return True
    except ImportError:
        return False


class TestNullBackend:
    def test_round_trip(self):
        backend = NullBackend()
        assert backend.decrypt(backend.encrypt("mysecrettoken")) == "mysecrettoken"

    def test_encrypted_differs_from_plaintext(self):
        backend = NullBackend()
        plaintext = "mysecrettoken"
        assert backend.encrypt(plaintext) != plaintext

    def test_empty_string_round_trip(self):
        backend = NullBackend()
        assert backend.decrypt(backend.encrypt("")) == ""

    def test_unicode_round_trip(self):
        backend = NullBackend()
        plaintext = "Tëst-Tökën-üäö"
        assert backend.decrypt(backend.encrypt(plaintext)) == plaintext

    def test_encrypt_returns_ascii_string(self):
        backend = NullBackend()
        result = backend.encrypt("hello")
        assert result.isascii()


@pytest.mark.skipif(
    not _win32crypt_available(),
    reason="pywin32 nicht installiert (pip install pywin32)",
)
class TestDpapiBackend:
    def test_round_trip(self):
        from qsl73.crypto import DpapiBackend
        backend = DpapiBackend()
        plaintext = "dpapi-testtoken"
        assert backend.decrypt(backend.encrypt(plaintext)) == plaintext

    def test_encrypted_differs_from_plaintext(self):
        from qsl73.crypto import DpapiBackend
        backend = DpapiBackend()
        plaintext = "dpapi-testtoken"
        assert backend.encrypt(plaintext) != plaintext


class TestGetDefaultBackend:
    def test_returns_usable_backend(self):
        if sys.platform == "win32" and not _win32crypt_available():
            pytest.skip("pywin32 nicht installiert")
        backend = get_default_backend()
        test_value = "hello"
        assert backend.decrypt(backend.encrypt(test_value)) == test_value

    def test_returns_null_backend_on_linux(self):
        if sys.platform == "win32":
            pytest.skip("Nur auf Nicht-Windows-Plattformen relevant")
        assert isinstance(get_default_backend(), NullBackend)

    def test_raises_on_windows_without_dpapi(self, monkeypatch):
        """Sicherheits-Regressionstest: Auf Windows ohne pywin32 KEIN NullBackend-Fallback.
        Simuliert Windows-Umgebung ohne funktionierendes DPAPI.
        Nur ausführbar wenn win32crypt tatsächlich nicht importierbar ist.
        """
        if _win32crypt_available():
            pytest.skip("pywin32 ist verfügbar; Test gilt nur für Umgebungen ohne pywin32")

        monkeypatch.setattr(sys, "platform", "win32")

        with pytest.raises(CryptoUnavailableError, match="pywin32"):
            get_default_backend()

    def test_raises_not_null_backend_on_windows_without_dpapi(self, monkeypatch):
        """Kein stiller NullBackend-Fallback: der Rückgabewert darf nie NullBackend sein
        wenn sys.platform == 'win32' und pywin32 fehlt — stattdessen muss Exception kommen.
        """
        if _win32crypt_available():
            pytest.skip("pywin32 ist verfügbar; Test gilt nur für Umgebungen ohne pywin32")

        monkeypatch.setattr(sys, "platform", "win32")

        try:
            backend = get_default_backend()
            # Wenn kein Fehler: sicherstellen dass es KEIN NullBackend ist
            assert not isinstance(backend, NullBackend), (
                "get_default_backend() darf auf Windows NICHT NullBackend zurückgeben"
            )
        except CryptoUnavailableError:
            pass  # Erwartetes Verhalten: Exception statt NullBackend
