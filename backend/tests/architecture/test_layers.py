from pathlib import Path

from importlinter.cli import lint_imports

BACKEND = Path(__file__).resolve().parents[2]


def test_import_contracts_in_pyproject_are_kept(monkeypatch):
    monkeypatch.chdir(BACKEND)

    assert lint_imports(config_filename="pyproject.toml", no_cache=True) == 0
