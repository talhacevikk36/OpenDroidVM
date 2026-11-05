import pytest


@pytest.fixture(autouse=True)
def _no_network_update_check(monkeypatch, tmp_path):
    monkeypatch.setenv("ODVM_NO_UPDATE_CHECK", "1")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
