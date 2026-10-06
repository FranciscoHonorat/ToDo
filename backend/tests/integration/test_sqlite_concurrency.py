from concurrent.futures import ThreadPoolExecutor

from domain.task import Task
from persistence.connection import get_connection
from persistence.sqlite_repository import SqliteRepository


def test_repository_shared_between_threads_does_not_fail_or_lose_tasks(tmp_path):
    connection = get_connection(str(tmp_path / "todo.db"), check_same_thread=False)
    repository = SqliteRepository(connection)
    tasks = [Task(f"Tarefa {n}", "") for n in range(200)]

    def add_and_read(task):
        repository.add_task(task)
        return repository.get_task_by_id(task.id).id

    with ThreadPoolExecutor(max_workers=16) as pool:
        found = list(pool.map(add_and_read, tasks))

    assert found == [task.id for task in tasks]
    assert len(repository.get_all_tasks()) == len(tasks)
    connection.close()
