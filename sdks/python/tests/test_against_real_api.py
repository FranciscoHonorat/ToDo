"""A SDK gerada contra a API de verdade (uvicorn + SQLite temporário)."""

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx2
import pytest

from todo_api_client import create_client, iter_tasks
from todo_api_client.generated.api.tasks import (
    complete_task,
    create_task,
    delete_task,
    get_task,
    list_tasks,
    reopen_task,
)
from todo_api_client.generated.models import ErrorResponse, Status, TaskInput

BACKEND = Path(__file__).resolve().parents[3] / "backend"
PYTHON = BACKEND / ".venv" / "bin" / "python"

pytestmark = pytest.mark.skipif(not PYTHON.exists(), reason="backend/.venv não instalado")


@pytest.fixture
def start_api(tmp_path):
    processes = []

    def start(rate_limit="off"):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = {**os.environ, "TODO_DATABASE": str(tmp_path / "sdk.db"), "TODO_RATE_LIMIT": rate_limit}
        env.pop("VIRTUAL_ENV", None)
        processes.append(
            subprocess.Popen(
                [str(PYTHON), "-m", "uvicorn", "server:app", "--port", str(port)],
                cwd=BACKEND,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
        url = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                if httpx2.get(f"{url}/health").status_code == 200:
                    return url
            except httpx2.TransportError:
                time.sleep(0.1)
        raise RuntimeError("uvicorn não subiu")

    yield start
    for process in processes:
        process.terminate()
        process.wait(timeout=10)


def test_full_journey(start_api):
    client = create_client(start_api())

    created = create_task.sync(client=client, body=TaskInput(title="Pelo SDK", description="py"))
    assert created.status is Status.PENDING

    assert complete_task.sync(client=client, task_id=created.id).status is Status.COMPLETED
    assert reopen_task.sync(client=client, task_id=created.id).status is Status.PENDING
    assert [t.title for t in iter_tasks(client)] == ["Pelo SDK"]

    assert delete_task.sync_detailed(client=client, task_id=created.id).status_code == 204
    missing = get_task.sync(client=client, task_id=created.id)
    assert isinstance(missing, ErrorResponse)
    assert "not found" in missing.detail


def test_retries_through_the_rate_limit(start_api):
    client = create_client(start_api(rate_limit="2/second"))

    statuses = [list_tasks.sync_detailed(client=client).status_code for _ in range(4)]

    assert statuses == [200, 200, 200, 200]
