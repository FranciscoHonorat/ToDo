from application.dto import TaskDTO

STATUS_MARK = {"PENDING": "[ ]", "COMPLETED": "[x]"}


def format_task(task: TaskDTO) -> str:
    line = f"{STATUS_MARK[task.status]} {task.id}  {task.title}"
    if task.description:
        line += f" — {task.description}"
    return line


def format_task_list(tasks: list[TaskDTO]) -> str:
    if not tasks:
        return "Nenhuma tarefa."
    return "\n".join(format_task(task) for task in tasks)
