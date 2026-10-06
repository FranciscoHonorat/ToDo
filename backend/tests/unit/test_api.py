import uuid

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from application.task_service import TaskService
from persistence.memory_repository import MemoryRepository


@pytest.fixture
def client():
    return TestClient(create_app(TaskService(MemoryRepository())))


def create(client, title="Comprar pão", description="na padaria"):
    return client.post("/tasks", json={"title": title, "description": description})


def test_create_task_returns_201_with_the_task(client):
    response = create(client)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Comprar pão"
    assert body["description"] == "na padaria"
    assert body["status"] == "PENDING"
    uuid.UUID(body["id"])


def test_create_task_without_description_defaults_to_empty(client):
    response = client.post("/tasks", json={"title": "Comprar pão"})

    assert response.json()["description"] == ""


def test_create_task_with_blank_title_returns_422(client):
    response = create(client, title="   ")

    assert response.status_code == 422
    assert response.json() == {"detail": "Title cannot be empty."}


def test_list_tasks_returns_created_tasks(client):
    create(client, title="A")
    create(client, title="B")

    response = client.get("/tasks")

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["A", "B"]


def test_list_tasks_filters_by_status(client):
    done = create(client, title="Done").json()
    create(client, title="Pending")
    client.post(f"/tasks/{done['id']}/complete")

    response = client.get("/tasks", params={"status": "completed"})

    assert [task["id"] for task in response.json()] == [done["id"]]


def test_list_tasks_with_invalid_status_returns_422(client):
    assert client.get("/tasks", params={"status": "whatever"}).status_code == 422


def test_get_task_returns_it(client):
    created = create(client).json()

    response = client.get(f"/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_complete_task_returns_completed_task(client):
    created = create(client).json()

    response = client.post(f"/tasks/{created['id']}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_edit_task_returns_edited_task(client):
    created = create(client).json()

    response = client.put(
        f"/tasks/{created['id']}", json={"title": "Novo", "description": "nova"}
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Novo"
    assert response.json()["description"] == "nova"


def test_delete_task_returns_204_and_removes_it(client):
    created = create(client).json()

    response = client.delete(f"/tasks/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/tasks/{created['id']}").status_code == 404


@pytest.mark.parametrize(
    "method, path_suffix, json",
    [
        ("get", "", None),
        ("put", "", {"title": "x"}),
        ("delete", "", None),
        ("post", "/complete", None),
    ],
)
def test_unknown_id_returns_404(client, method, path_suffix, json):
    response = client.request(method, f"/tasks/{uuid.uuid4()}{path_suffix}", json=json)

    assert response.status_code == 404


def test_malformed_id_returns_422(client):
    assert client.get("/tasks/not-a-uuid").status_code == 422


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
