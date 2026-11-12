"""O filtro por status precisa usar índice: sem ele a listagem lê a tabela
inteira e ordena em memória, e fica mais lenta conforme o banco cresce."""

from persistence.connection import get_connection
from persistence.sqlite_repository import COUNT_BY_STATUS, LIST_BY_STATUS


def query_plan(sql, parameters):
    connection = get_connection(":memory:")
    try:
        return " | ".join(row[-1] for row in connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters))
    finally:
        connection.close()


def test_listing_by_status_uses_an_index_without_sorting():
    plan = query_plan(LIST_BY_STATUS, ("PENDING", 50, 0))

    assert "USING INDEX" in plan, plan
    assert "TEMP B-TREE" not in plan, plan


def test_counting_by_status_uses_an_index():
    plan = query_plan(COUNT_BY_STATUS, ("PENDING",))

    assert "USING COVERING INDEX" in plan, plan
