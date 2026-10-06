import argparse
import sys
import uuid

from application.dto import TaskDTO
from application.task_service import TaskService
from domain.exceptions import InvalidTitleError, TaskNotFoundError
from domain.status import Status
from ui.formt import format_task, format_task_list


def build_parser():
    parser = argparse.ArgumentParser(prog="todo", description="Gerenciador de tarefas")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="cria uma tarefa")
    add.add_argument("title")
    add.add_argument("description", nargs="?", default="")

    list_ = commands.add_parser("list", help="lista tarefas")
    list_.add_argument("--status", choices=[s.value.lower() for s in Status])

    done = commands.add_parser("done", help="marca uma tarefa como concluída")
    done.add_argument("id", type=uuid.UUID)

    edit = commands.add_parser("edit", help="edita uma tarefa")
    edit.add_argument("id", type=uuid.UUID)
    edit.add_argument("title")
    edit.add_argument("description", nargs="?", default="")

    delete = commands.add_parser("delete", help="remove uma tarefa")
    delete.add_argument("id", type=uuid.UUID)

    return parser


def run(service: TaskService, argv=None, out=sys.stdout, err=sys.stderr) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "add":
            task = service.create_task(args.title, args.description)
            print(f"Criada: {format_task(TaskDTO.from_task(task))}", file=out)
        elif args.command == "list":
            status = Status(args.status.upper()) if args.status else None
            tasks = [TaskDTO.from_task(t) for t in service.list_tasks(status)]
            print(format_task_list(tasks), file=out)
        elif args.command == "done":
            task = service.complete_task(args.id)
            print(f"Concluída: {format_task(TaskDTO.from_task(task))}", file=out)
        elif args.command == "edit":
            task = service.edit_task(args.id, args.title, args.description)
            print(f"Editada: {format_task(TaskDTO.from_task(task))}", file=out)
        elif args.command == "delete":
            service.delete_task(args.id)
            print(f"Removida: {args.id}", file=out)
    except (InvalidTitleError, TaskNotFoundError) as error:
        print(f"Erro: {error}", file=err)
        return 1
    return 0
