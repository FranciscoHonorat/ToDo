import os
from pathlib import Path

from application.task_service import TaskService
from persistence.connection import get_connection
from persistence.sqlite_repository import SqliteRepository

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "db" / "todo.db"


def database_path() -> str:
    return os.environ.get("TODO_DATABASE", str(DEFAULT_DATABASE_PATH))


def build_service(connection) -> TaskService:
    return TaskService(SqliteRepository(connection))
