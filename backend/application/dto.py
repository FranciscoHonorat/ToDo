from dataclasses import dataclass

from domain.task import Task


@dataclass(frozen=True)
class TaskDTO:
    id: str
    title: str
    description: str
    status: str

    @classmethod
    def from_task(cls, task: Task) -> "TaskDTO":
        return cls(
            id=str(task.id),
            title=task.title,
            description=task.description,
            status=task.status.value,
        )
