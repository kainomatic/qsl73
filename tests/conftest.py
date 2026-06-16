import pytest
from qsl73.crypto import NullBackend


@pytest.fixture
def null_crypto():
    return NullBackend()


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / "config.yaml"
