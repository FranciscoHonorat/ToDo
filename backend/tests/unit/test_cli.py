import io

from application.task_service import TaskService
from persistence.memory_repository import MemoryRepository
from ui import cli


def run(service, *argv):
    out, err = io.StringIO(), io.StringIO()
    code = cli.run(service, list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_add_then_list_shows_the_task():
    service = TaskService(MemoryRepository())

    run(service, "add", "Comprar pão", "na padaria")
    code, out, _ = run(service, "list")

    assert code == 0
    assert "[ ]" in out
    assert "Comprar pão — na padaria" in out


def test_done_marks_task_as_completed():
    service = TaskService(MemoryRepository())
    task = service.create_task("Comprar pão", "")

    run(service, "done", str(task.id))
    _, out, _ = run(service, "list", "--status", "completed")

    assert "[x]" in out
    assert "Comprar pão" in out


def test_empty_title_prints_error_and_returns_1():
    service = TaskService(MemoryRepository())

    code, _, err = run(service, "add", "   ")

    assert code == 1
    assert "Erro" in err


def test_unknown_id_prints_error_and_returns_1():
    service = TaskService(MemoryRepository())

    code, _, err = run(service, "delete", "00000000-0000-0000-0000-000000000000")

    assert code == 1
    assert "Erro" in err
