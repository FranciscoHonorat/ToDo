import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from composition import build_service
from persistence.connection import get_connection


def make_client(database):
    connection = get_connection(str(database), check_same_thread=False)
    return TestClient(create_app(build_service(connection))), connection


@pytest.fixture
def database(tmp_path):
    return tmp_path / "todo.db"


def rows(database):
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT title, description, status FROM tasks").fetchall()


def test_task_lifecycle_is_persisted_in_sqlite(database):
    client, connection = make_client(database)

    created = client.post("/tasks", json={"title": "Comprar pão", "description": "padaria"}).json()
    assert rows(database) == [("Comprar pão", "padaria", "PENDING")]

    client.put(f"/tasks/{created['id']}", json={"title": "Comprar leite", "description": ""})
    client.post(f"/tasks/{created['id']}/complete")
    assert rows(database) == [("Comprar leite", "", "COMPLETED")]

    client.delete(f"/tasks/{created['id']}")
    assert rows(database) == []
    connection.close()


def test_tasks_survive_an_application_restart(database):
    first, connection = make_client(database)
    created = first.post("/tasks", json={"title": "Persistente"}).json()
    connection.close()

    second, connection = make_client(database)
    response = second.get(f"/tasks/{created['id']}")
    connection.close()

    assert response.status_code == 200
    assert response.json() == created


def test_status_filter_runs_against_sqlite(database):
    client, connection = make_client(database)
    done = client.post("/tasks", json={"title": "Done"}).json()
    client.post("/tasks", json={"title": "Pending"})
    client.post(f"/tasks/{done['id']}/complete")

    pending = client.get("/tasks", params={"status": "pending"}).json()
    connection.close()

    assert [task["title"] for task in pending] == ["Pending"]


def test_server_uses_database_from_environment(database, monkeypatch):
    monkeypatch.setenv("TODO_DATABASE", str(database))
    server = importlib.reload(importlib.import_module("server"))

    TestClient(server.app).post("/tasks", json={"title": "Pelo server.py"})
    server.connection.close()

    assert rows(database) == [("Pelo server.py", "", "PENDING")]


def test_server_uses_root_path_from_environment(database, monkeypatch):
    monkeypatch.setenv("TODO_DATABASE", str(database))
    monkeypatch.setenv("API_ROOT_PATH", "/api")
    server = importlib.reload(importlib.import_module("server"))

    spec = TestClient(server.app).get("/openapi.json").json()
    server.connection.close()

    assert spec["servers"] == [{"url": "/api"}]
