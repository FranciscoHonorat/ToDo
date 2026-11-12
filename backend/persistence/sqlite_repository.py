import sqlite3
import threading
import uuid

from domain.status import Status
from domain.task import Task

# Queries fixas (sem montar SQL com f-string): o valor do filtro sempre vai como parâmetro.
LIST_ALL = "SELECT id, title, description, status FROM tasks ORDER BY created_at, rowid LIMIT ? OFFSET ?"
LIST_BY_STATUS = (
    "SELECT id, title, description, status FROM tasks WHERE status = ? ORDER BY created_at, rowid LIMIT ? OFFSET ?"
)
COUNT_ALL = "SELECT COUNT(*) FROM tasks"
COUNT_BY_STATUS = "SELECT COUNT(*) FROM tasks WHERE status = ?"


class SqliteRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        # Uma conexão sqlite3 não pode ter cursores/transações intercalados entre
        # threads (o FastAPI roda rotas síncronas num pool de threads).
        self._lock = threading.Lock()

    def add_task(self, task):
        self._write(
            "INSERT INTO tasks (id, title, description, status) VALUES (?, ?, ?, ?)",
            (str(task.id), task.title, task.description, task.status.value),
        )

    def get_all_tasks(self):
        return self.find_tasks()

    def find_tasks(self, status=None, limit=None, offset=0):
        # LIMIT -1 = sem limite no SQLite; o OFFSET exige um LIMIT.
        page = (-1 if limit is None else limit, offset)
        if status is None:
            rows = self._read(LIST_ALL, page)
        else:
            rows = self._read(LIST_BY_STATUS, (status.value, *page))
        return [self._to_task(row) for row in rows]

    def count_tasks(self, status=None):
        if status is None:
            return self._read(COUNT_ALL)[0][0]
        return self._read(COUNT_BY_STATUS, (status.value,))[0][0]

    def get_task_by_id(self, task_id: uuid.UUID):
        rows = self._read("SELECT id, title, description, status FROM tasks WHERE id = ?", (str(task_id),))
        return self._to_task(rows[0]) if rows else None

    def update_task(self, task):
        self._write(
            "UPDATE tasks SET title = ?, description = ?, status = ? WHERE id = ?",
            (task.title, task.description, task.status.value, str(task.id)),
        )

    def delete_task(self, task_id: uuid.UUID):
        self._write("DELETE FROM tasks WHERE id = ?", (str(task_id),))

    def _read(self, sql, parameters=()):
        with self._lock:
            return self.connection.execute(sql, parameters).fetchall()

    def _write(self, sql, parameters):
        with self._lock, self.connection:
            self.connection.execute(sql, parameters)

    @staticmethod
    def _to_task(row):
        id, title, description, status = row
        return Task(title, description, id=uuid.UUID(id), status=Status(status))
