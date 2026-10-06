import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def get_connection(database=":memory:", check_same_thread=True):
    connection = sqlite3.connect(database, check_same_thread=check_same_thread)
    connection.executescript(SCHEMA_PATH.read_text())
    return connection
