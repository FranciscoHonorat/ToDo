import sqlite3
import threading
import uuid

from domain.status import Status
from domain.task import Task


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
        where, parameters = self._status_filter(status)
        # LIMIT -1 = sem limite no SQLite; o OFFSET exige um LIMIT.
        rows = self._read(
            f"SELECT id, title, description, status FROM tasks{where} ORDER BY created_at, rowid LIMIT ? OFFSET ?",
            (*parameters, -1 if limit is None else limit, offset),
        )
        return [self._to_task(row) for row in rows]

    def count_tasks(self, status=None):
        where, parameters = self._status_filter(status)
        return self._read(f"SELECT COUNT(*) FROM tasks{where}", parameters)[0][0]

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
    def _status_filter(status):
        return (" WHERE status = ?", (status.value,)) if status else ("", ())

    @staticmethod
    def _to_task(row):
        id, title, description, status = row
        return Task(title, description, id=uuid.UUID(id), status=Status(status))
