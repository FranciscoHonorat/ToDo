from dataclasses import dataclass

from domain.task import Task
from domain.task_repository import TaskRepository
from domain.exceptions import TaskNotFoundError


@dataclass(frozen=True)
class TaskPage:
    items: list[Task]
    total: int  # quantas tarefas existem com o filtro, ignorando limit/offset


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def create_task(self, title, description):
        task = Task(title, description)
        self.repository.add_task(task)
        return task

    def list_tasks(self, status=None):
        return self.repository.find_tasks(status)

    def list_page(self, status=None, limit=None, offset=0):
        items = self.repository.find_tasks(status, limit, offset)
        return TaskPage(items, self.repository.count_tasks(status))

    def get_task_by_id(self, task_id):
        task = self.repository.get_task_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(f"Task with ID {task_id} not found.")
        return task

    def complete_task(self, task_id):
        task = self.get_task_by_id(task_id)
        task.complete()
        self.repository.update_task(task)
        return task

    def edit_task(self, task_id, title, description):
        task = self.get_task_by_id(task_id)
        task.edit(title, description)
        self.repository.update_task(task)
        return task

    def delete_task(self, task_id):
        self.get_task_by_id(task_id)
        self.repository.delete_task(task_id)
