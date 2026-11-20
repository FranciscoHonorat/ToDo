import json

import httpx2
import pytest

from todo_api_client import RetryOn429Transport, create_client, iter_tasks
from todo_api_client.generated.api.tasks import list_tasks
from todo_api_client.generated.models import StatusFilter


def task(n):
    return {"id": f"00000000-0000-0000-0000-00000000000{n}", "title": f"T{n}", "description": "", "status": "PENDING"}


class Script:
    """Transporte falso: devolve as respostas na ordem e guarda as requisições."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        return self.responses.pop(0)


def test_retry_transport_waits_retry_after_and_retries():
    script = Script(httpx2.Response(429, headers={"Retry-After": "2"}), httpx2.Response(200, json=[]))
    slept = []
    transport = RetryOn429Transport(httpx2.MockTransport(script), sleep=slept.append)

    response = httpx2.Client(transport=transport).get("http://api/tasks")

    assert response.status_code == 200
    assert slept == [2]
    assert len(script.requests) == 2


def test_retry_transport_gives_up_after_max_retries():
    script = Script(*[httpx2.Response(429, headers={"Retry-After": "1"}) for _ in range(3)])
    transport = RetryOn429Transport(httpx2.MockTransport(script), max_retries=2, sleep=lambda s: None)

    response = httpx2.Client(transport=transport).get("http://api/tasks")

    assert response.status_code == 429
    assert len(script.requests) == 3


def test_retry_transport_does_not_wait_longer_than_max_delay():
    slept = []
    script = Script(httpx2.Response(429, headers={"Retry-After": "3600"}))
    transport = RetryOn429Transport(httpx2.MockTransport(script), max_delay_seconds=30, sleep=slept.append)

    response = httpx2.Client(transport=transport).get("http://api/tasks")

    assert response.status_code == 429
    assert slept == []


def test_create_client_talks_to_the_api_with_typed_models():
    script = Script(httpx2.Response(200, json=[task(1)], headers={"X-Total-Count": "1"}))
    client = create_client("http://api", transport=httpx2.MockTransport(script))

    tasks = list_tasks.sync(client=client, status=StatusFilter.PENDING, limit=10)

    assert [t.title for t in tasks] == ["T1"]
    assert str(script.requests[0].url) == "http://api/tasks?status=pending&limit=10&offset=0"


def test_iter_tasks_walks_every_page():
    all_tasks = [task(n) for n in range(1, 6)]

    def handler(request):
        limit = int(request.url.params["limit"])
        offset = int(request.url.params["offset"])
        page = all_tasks[offset : offset + limit]
        return httpx2.Response(200, json=page, headers={"X-Total-Count": str(len(all_tasks))})

    client = create_client("http://api", transport=httpx2.MockTransport(handler))

    assert [t.title for t in iter_tasks(client, page_size=2)] == ["T1", "T2", "T3", "T4", "T5"]


def test_iter_tasks_raises_on_error():
    def handler(request):
        return httpx2.Response(422, content=json.dumps({"detail": [{"msg": "x", "loc": [], "type": "t"}]}))

    client = create_client("http://api", transport=httpx2.MockTransport(handler))

    with pytest.raises(RuntimeError, match="GET /tasks falhou com 422"):
        list(iter_tasks(client))
