import pytest
import uuid

from domain.status import Status
from domain.task import Task
from domain.exceptions import InvalidTitleError

def test_task_creation():
    task = Task(title="Test Task", description="This is a test task.")
    assert task.title == "Test Task"
    assert task.description == "This is a test task."


def test_new_task_starts_as_pending():
    task = Task(title="Test Task", description="This is a test task.")
    assert task.status == Status.PENDING

def test_complete_marks_task_as_completed():
    task = Task(title="Test Task", description="This is a test task.")

    task.complete()
    
    assert task.status == Status.COMPLETED

def test_empty_title_raises_invalid_title_error():
    with pytest.raises(InvalidTitleError):
        Task(title="", description="This is a test task.")

def test_whitespace_title_raises_invalid_title_error():
    with pytest.raises(InvalidTitleError):
        Task(title="   ", description="This is a test task.")

def test_valid_task1_id_is_different_from_valid_task2_id():
    task1 = Task(title="Task 1", description="First task.")
    task2 = Task(title="Task 2", description="Second task.")

    assert task1.id != task2.id


def test_task_can_be_rebuilt_with_existing_id_and_status():
    existing_id = uuid.uuid4()

    task = Task("Test Task", "", id=existing_id, status=Status.COMPLETED)

    assert task.id == existing_id
    assert task.status == Status.COMPLETED

def test_edit_changes_title_and_description():
    task = Task(title="Old", description="Old description")

    task.edit("New", "New description")

    assert task.title == "New"
    assert task.description == "New description"

def test_edit_with_empty_title_raises_and_keeps_old_title():
    task = Task(title="Old", description="Old description")

    with pytest.raises(InvalidTitleError):
        task.edit("  ", "New description")

    assert task.title == "Old"
