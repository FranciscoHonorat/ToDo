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


def add_tasks(repository, *titles, completed=()):
    tasks = []
    for title in titles:
        task = Task(title, "")
        if title in completed:
            task.complete()
        repository.add_task(task)
        tasks.append(task)
    return tasks


def test_find_tasks_without_filters_returns_all_in_order(repository):
    tasks = add_tasks(repository, "A", "B", "C")

    assert [task.id for task in repository.find_tasks()] == [task.id for task in tasks]


def test_find_tasks_filters_by_status_keeping_order(repository):
    a, _, c = add_tasks(repository, "A", "B", "C", completed=("B",))

    found = repository.find_tasks(status=Status.PENDING)

    assert [task.id for task in found] == [a.id, c.id]


def test_find_tasks_limit_and_offset_page_through_results(repository):
    tasks = add_tasks(repository, "A", "B", "C", "D", "E")

    page = repository.find_tasks(limit=2, offset=1)

    assert [task.id for task in page] == [tasks[1].id, tasks[2].id]


def test_find_tasks_pages_after_filtering(repository):
    _, b, _, d, e = add_tasks(repository, "A", "B", "C", "D", "E", completed=("A", "C"))

    first = repository.find_tasks(status=Status.PENDING, limit=2)
    second = repository.find_tasks(status=Status.PENDING, limit=2, offset=2)

    assert [task.id for task in first] == [b.id, d.id]
    assert [task.id for task in second] == [e.id]


def test_find_tasks_offset_past_the_end_returns_empty(repository):
    add_tasks(repository, "A")

    assert repository.find_tasks(offset=5) == []


def test_count_tasks_by_status(repository):
    add_tasks(repository, "A", "B", "C", completed=("B",))

    assert repository.count_tasks() == 3
    assert repository.count_tasks(status=Status.PENDING) == 2
    assert repository.count_tasks(status=Status.COMPLETED) == 1
