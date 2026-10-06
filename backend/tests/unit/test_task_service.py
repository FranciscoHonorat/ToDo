from application.task_service import TaskService
from domain.exceptions import TaskNotFoundError
from domain.status import Status
from persistence.memory_repository import MemoryRepository
import pytest
import uuid


def test_created_task_appears_in_list():
    memory = MemoryRepository()
    service = TaskService(memory)
    service.create_task("Test Task", "Test Description")
    tasks = service.list_tasks()

    assert len(tasks) == 1
    assert tasks[0].title == "Test Task"
    assert tasks[0].description == "Test Description"


def test_create_task_returns_the_created_task():
    memory = MemoryRepository()
    service = TaskService(memory)

    task = service.create_task("Test Task", "Test Description")

    assert task.title == "Test Task"
    assert task.description == "Test Description"


def test_get_task_returns_task_by_id():
    memory = MemoryRepository()
    service = TaskService(memory)
    created = service.create_task("Test Task", "Test Description")

    found = service.get_task_by_id(created.id)

    assert found.id == created.id


def test_complete_task_marks_it_as_completed():
    memory = MemoryRepository()
    service = TaskService(memory)
    task = service.create_task("Test Task", "Test Description")

    service.complete_task(task.id)

    assert task.status is Status.COMPLETED


def test_complete_task_with_unknown_id_raises_task_not_found_error():
    memory = MemoryRepository()
    service = TaskService(memory)
    with pytest.raises(TaskNotFoundError):
        service.complete_task(uuid.uuid4())


def test_get_task_by_id_with_unknown_id_raises_task_not_found_error():
    memory = MemoryRepository()
    service = TaskService(memory)
    with pytest.raises(TaskNotFoundError):
        service.get_task_by_id(uuid.uuid4())


def test_complete_task_is_persisted_in_repository():
    memory = MemoryRepository()
    service = TaskService(memory)
    task = service.create_task("Test Task", "Test Description")

    service.complete_task(task.id)

    assert memory.get_task_by_id(task.id).status is Status.COMPLETED


def test_list_tasks_filters_by_status():
    memory = MemoryRepository()
    service = TaskService(memory)
    done = service.create_task("Done", "")
    service.create_task("Pending", "")
    service.complete_task(done.id)

    completed = service.list_tasks(Status.COMPLETED)

    assert [task.id for task in completed] == [done.id]


def test_edit_task_changes_title_and_description():
    memory = MemoryRepository()
    service = TaskService(memory)
    task = service.create_task("Old", "Old description")

    service.edit_task(task.id, "New", "New description")

    found = service.get_task_by_id(task.id)
    assert found.title == "New"
    assert found.description == "New description"


def test_edit_task_with_unknown_id_raises_task_not_found_error():
    service = TaskService(MemoryRepository())
    with pytest.raises(TaskNotFoundError):
        service.edit_task(uuid.uuid4(), "New", "")


def test_delete_task_removes_it_from_list():
    memory = MemoryRepository()
    service = TaskService(memory)
    task = service.create_task("Test Task", "")

    service.delete_task(task.id)

    assert service.list_tasks() == []


def test_delete_task_with_unknown_id_raises_task_not_found_error():
    service = TaskService(MemoryRepository())
    with pytest.raises(TaskNotFoundError):
        service.delete_task(uuid.uuid4())
