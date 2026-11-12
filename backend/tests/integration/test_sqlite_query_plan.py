"""O filtro por status precisa usar índice: sem ele a listagem lê a tabela
inteira e ordena em memória, e fica mais lenta conforme o banco cresce."""

from persistence.connection import get_connection

LIST_PENDING = (
    "SELECT id, title, description, status FROM tasks WHERE status = ? "
    "ORDER BY created_at, rowid LIMIT ? OFFSET ?"
)


def query_plan(sql, parameters):
    connection = get_connection(":memory:")
    try:
        return " | ".join(row[-1] for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters))
    finally:
        connection.close()


def test_listing_by_status_uses_an_index_without_sorting():
    plan = query_plan(LIST_PENDING, ("PENDING", 50, 0))

    assert "USING INDEX" in plan, plan
    assert "TEMP B-TREE" not in plan, plan


def test_counting_by_status_uses_an_index():
    plan = query_plan("SELECT COUNT(*) FROM tasks WHERE status = ?", ("PENDING",))

    assert "USING COVERING INDEX" in plan, plan
