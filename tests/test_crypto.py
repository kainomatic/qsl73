import sys
import pytest
from qsl73.crypto import NullBackend, get_default_backend


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
        from qsl73.crypto import NullBackend
        assert isinstance(get_default_backend(), NullBackend)
