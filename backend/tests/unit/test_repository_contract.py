import uuid

import pytest

from domain.status import Status
from domain.task import Task
from persistence.connection import get_connection
from persistence.memory_repository import MemoryRepository
from persistence.sqlite_repository import SqliteRepository


@pytest.fixture(params=["memory", "sqlite"])
def repository(request):
    if request.param == "memory":
        yield MemoryRepository()
    else:
        connection = get_connection(":memory:")
        yield SqliteRepository(connection)
        connection.close()


def test_added_task_can_be_found_by_id(repository):
    task = Task("Test Task", "Test Description")

    repository.add_task(task)
    found = repository.get_task_by_id(task.id)

    assert found.id == task.id
    assert found.title == "Test Task"
    assert found.description == "Test Description"
    assert found.status is Status.PENDING


def test_unknown_id_returns_none(repository):
    assert repository.get_task_by_id(uuid.uuid4()) is None


def test_get_all_tasks_returns_added_tasks_in_order(repository):
    first = Task("First", "")
    second = Task("Second", "")
    repository.add_task(first)
    repository.add_task(second)

    ids = [task.id for task in repository.get_all_tasks()]

    assert ids == [first.id, second.id]


def test_update_task_persists_changes(repository):
    task = Task("Old title", "Old description")
    repository.add_task(task)

    task.edit("New title", "New description")
    task.complete()
    repository.update_task(task)
    found = repository.get_task_by_id(task.id)

    assert found.title == "New title"
    assert found.description == "New description"
    assert found.status is Status.COMPLETED


def test_delete_task_removes_it(repository):
    task = Task("Test Task", "")
    repository.add_task(task)

    repository.delete_task(task.id)

    assert repository.get_task_by_id(task.id) is None
    assert repository.get_all_tasks() == []
