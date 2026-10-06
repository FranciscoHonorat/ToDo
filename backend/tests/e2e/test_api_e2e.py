import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from openapi_contract import assert_matches_spec

pytestmark = pytest.mark.e2e


def call(server, method, path, body=None, raw=None):
    """Toda resposta do servidor real precisa bater com o docs/openapi.yaml."""
    status, data = server.call(method, path, body, raw)
    assert_matches_spec(method, path, status, data)
    return status, data


def test_full_task_journey(server):
    status, created = call(server, "POST", "/tasks", {"title": "Comprar pão", "description": "padaria"})
    assert status == 201
    task = f"/tasks/{created['id']}"

    assert call(server, "GET", task) == (200, created)
    assert call(server, "GET", "/tasks")[1] == [created]

    status, edited = call(server, "PUT", task, {"title": "Comprar leite", "description": ""})
    assert (status, edited["title"], edited["status"]) == (200, "Comprar leite", "PENDING")

    status, completed = call(server, "POST", f"{task}/complete")
    assert (status, completed["status"]) == (200, "COMPLETED")
    assert call(server, "GET", "/tasks?status=completed")[1] == [completed]
    assert call(server, "GET", "/tasks?status=pending")[1] == []

    assert call(server, "DELETE", task) == (204, None)
    assert call(server, "GET", task)[0] == 404


@pytest.mark.parametrize(
    "method, path, body, raw, expected",
    [
        ("POST", "/tasks", {"title": "   "}, None, 422),
        ("POST", "/tasks", {"description": "sem título"}, None, 422),
        ("POST", "/tasks", None, b"{json quebrado", 422),
        ("GET", "/tasks?status=whatever", None, None, 422),
        ("GET", "/tasks/not-a-uuid", None, None, 422),
        ("GET", f"/tasks/{uuid.uuid4()}", None, None, 404),
        ("PUT", f"/tasks/{uuid.uuid4()}", {"title": "x"}, None, 404),
        ("POST", f"/tasks/{uuid.uuid4()}/complete", None, None, 404),
        ("DELETE", f"/tasks/{uuid.uuid4()}", None, None, 404),
    ],
)
def test_errors_are_returned_as_documented(server, method, path, body, raw, expected):
    status, _ = call(server, method, path, body, raw)

    assert status == expected


def test_data_survives_a_real_server_restart(make_server, tmp_path):
    database = tmp_path / "restart.db"
    first = make_server(database)
    _, created = call(first, "POST", "/tasks", {"title": "Persistente"})
    first.stop()

    second = make_server(database)

    assert call(second, "GET", f"/tasks/{created['id']}") == (200, created)


def test_concurrent_requests_do_not_lose_tasks(server):
    titles = [f"Tarefa {n}" for n in range(30)]

    with ThreadPoolExecutor(max_workers=10) as pool:
        statuses = list(pool.map(lambda t: call(server, "POST", "/tasks", {"title": t})[0], titles))

    assert statuses == [201] * len(titles)
    assert sorted(t["title"] for t in call(server, "GET", "/tasks")[1]) == sorted(titles)
