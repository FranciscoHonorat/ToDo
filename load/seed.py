"""Popula um banco SQLite novo com um volume declarado de tarefas, antes de subir a API.

Uso (a partir de backend/, para usar o mesmo schema e índices da aplicação):
    python ../load/seed.py BANCO --total 10000 --pending-pct 50 [--ids ARQUIVO]

Gravar direto no banco com executemany leva menos de 1 s para 100 mil tarefas;
via POST /tasks seriam minutos. As tarefas recebem created_at no passado (uma por
segundo), então as criadas durante o teste ficam no fim da ordem de listagem.
"""

import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from persistence.connection import get_connection  # noqa: E402


def is_pending(index: int, pending_pct: int) -> bool:
    # Espalha as pendentes de forma uniforme (pct=50 alterna P, C, P, C...).
    return (index * pending_pct) // 100 != ((index + 1) * pending_pct) // 100


def rows(total: int, pending_pct: int):
    for index in range(total):
        status = "PENDING" if is_pending(index, pending_pct) else "COMPLETED"
        yield str(uuid.uuid4()), f"seed {index}", "carga", status, total - index


def seed(database: str, total: int, pending_pct: int) -> list[str]:
    connection = get_connection(database)
    try:
        with connection:
            connection.executemany(
                "INSERT INTO tasks (id, title, description, status, created_at) "
                "VALUES (?, ?, ?, ?, datetime('now', '-' || ? || ' seconds'))",
                rows(total, pending_pct),
            )
        return [row[0] for row in connection.execute("SELECT id FROM tasks ORDER BY rowid")]
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("database")
    parser.add_argument("--total", type=int, required=True)
    parser.add_argument("--pending-pct", type=int, default=50, choices=range(0, 101), metavar="0-100")
    parser.add_argument("--ids", help="arquivo onde gravar os ids (um por linha)")
    args = parser.parse_args()

    ids = seed(args.database, args.total, args.pending_pct)
    if args.ids:
        Path(args.ids).write_text("".join(f"{task_id}\n" for task_id in ids))


if __name__ == "__main__":
    main()
