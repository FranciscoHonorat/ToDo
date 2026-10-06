import os
import re
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]


def cli(database, *args):
    return subprocess.run(
        [sys.executable, "main.py", *args],
        cwd=BACKEND,
        env={**os.environ, "TODO_DATABASE": str(database)},
        capture_output=True,
        text=True,
    )


def test_cli_process_persists_tasks_between_runs(tmp_path):
    database = tmp_path / "todo.db"

    added = cli(database, "add", "Comprar pão", "padaria")
    task_id = re.search(r"[0-9a-f-]{36}", added.stdout).group()
    cli(database, "done", task_id)
    listed = cli(database, "list", "--status", "completed")

    assert added.returncode == 0
    assert f"[x] {task_id}  Comprar pão — padaria" in listed.stdout


def test_cli_process_returns_1_and_writes_to_stderr_on_error(tmp_path):
    result = cli(tmp_path / "todo.db", "add", "   ")

    assert result.returncode == 1
    assert result.stdout == ""
    assert "Erro: Title cannot be empty." in result.stderr
