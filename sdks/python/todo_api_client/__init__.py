"""SDK Python da ToDo API.

- ``todo_api_client.generated`` é GERADO a partir de docs/openapi.yaml (``make sdk-python``) — não edite.
- Este módulo é a camada fina escrita à mão: cliente com retry no 429 e paginação.

Exemplo::

    from todo_api_client import create_client, iter_tasks
    from todo_api_client.generated.api.tasks import create_task
    from todo_api_client.generated.models import TaskInput

    client = create_client("http://localhost:8080/api")
    create_task.sync(client=client, body=TaskInput(title="Comprar pão"))
    for task in iter_tasks(client, status="pending"):
        print(task.title)
"""

import time
from collections.abc import Callable, Iterator
from http import HTTPStatus

import httpx2

from todo_api_client.generated.api.tasks import list_tasks
from todo_api_client.generated.client import Client
from todo_api_client.generated.models import StatusFilter, TaskOutput

__all__ = ["Client", "RetryOn429Transport", "create_client", "iter_tasks"]


class RetryOn429Transport(httpx2.BaseTransport):
    """Repete requisições que recebem 429, esperando o ``Retry-After`` (em segundos)."""

    def __init__(
        self,
        inner: httpx2.BaseTransport,
        *,
        max_retries: int = 3,
        max_delay_seconds: float = 60,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.inner = inner
        self.max_retries = max_retries
        self.max_delay_seconds = max_delay_seconds
        self.sleep = sleep

    def handle_request(self, request: httpx2.Request) -> httpx2.Response:
        for attempt in range(self.max_retries + 1):
            response = self.inner.handle_request(request)
            if response.status_code != HTTPStatus.TOO_MANY_REQUESTS or attempt == self.max_retries:
                return response
            try:
                delay = float(response.headers.get("Retry-After", "1"))
            except ValueError:
                return response
            if delay > self.max_delay_seconds:
                return response
            response.close()
            self.sleep(delay)
        return response  # inalcançável; satisfaz o type checker

    def close(self) -> None:
        self.inner.close()


def create_client(
    base_url: str,
    *,
    max_retries: int = 3,
    max_delay_seconds: float = 60,
    timeout: float = 10.0,
    transport: httpx2.BaseTransport | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Client:
    """Cliente gerado, já com retry no 429. ``base_url`` ex.: ``http://localhost:8080/api``."""
    retrying = RetryOn429Transport(
        transport or httpx2.HTTPTransport(),
        max_retries=max_retries,
        max_delay_seconds=max_delay_seconds,
        sleep=sleep,
    )
    return Client(base_url=base_url, timeout=httpx2.Timeout(timeout), httpx_args={"transport": retrying})


def iter_tasks(client: Client, *, status: StatusFilter | str | None = None, page_size: int = 100) -> Iterator[TaskOutput]:
    """Percorre todas as tarefas, página por página (limit/offset + X-Total-Count)."""
    status_filter = StatusFilter(status) if status is not None else None
    offset = 0
    while True:
        response = list_tasks.sync_detailed(client=client, status=status_filter, limit=page_size, offset=offset)
        if response.status_code != HTTPStatus.OK or not isinstance(response.parsed, list):
            raise RuntimeError(f"GET /tasks falhou com {int(response.status_code)}")
        yield from response.parsed

        offset += len(response.parsed)
        total = int(response.headers.get("X-Total-Count", "0"))
        if len(response.parsed) < page_size or offset >= total:
            return
