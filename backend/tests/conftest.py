import pytest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """Nenhum teste pode tocar o banco real em db/todo.db."""
    monkeypatch.setenv("TODO_DATABASE", str(tmp_path / "isolated.db"))
