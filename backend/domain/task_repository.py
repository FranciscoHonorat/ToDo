from typing import Protocol
import uuid

from domain.task import Task


class TaskRepository(Protocol):
    def add_task(self, task: Task) -> None:
        ...

    def get_all_tasks(self) -> list[Task]:
        ...

    def get_task_by_id(self, task_id: uuid.UUID) -> Task | None:
        ...

    def update_task(self, task: Task) -> None:
        ...

    def delete_task(self, task_id: uuid.UUID) -> None:
        ...
