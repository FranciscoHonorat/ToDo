import uuid

from fastapi import FastAPI, Query, Request, status
from fastapi.responses import JSONResponse, Response

from api.schemas import (
    INVALID_TASK,
    NOT_FOUND,
    HealthOutput,
    StatusFilter,
    TaskInput,
    TaskOutput,
    to_status,
)
from application.task_service import TaskService
from domain.exceptions import InvalidTitleError, TaskNotFoundError

ERROR_STATUS = {
    InvalidTitleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    TaskNotFoundError: status.HTTP_404_NOT_FOUND,
}

DESCRIPTION = """API de tarefas do projeto ToDo.

Erros de regra de negócio retornam `{"detail": "<mensagem>"}`; erros de formato
(JSON inválido, UUID malformado, status desconhecido) seguem o padrão do FastAPI,
com `detail` sendo uma lista.
"""

TAGS = [
    {"name": "tasks", "description": "Criação, consulta, edição, conclusão e remoção de tarefas."},
    {"name": "infra", "description": "Endpoints operacionais (healthcheck)."},
]


def create_app(service: TaskService, root_path: str = "") -> FastAPI:
    app = FastAPI(
        title="ToDo API",
        version="0.1.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        root_path=root_path,
        generate_unique_id_function=lambda route: route.name,
    )

    for error, code in ERROR_STATUS.items():
        app.add_exception_handler(error, _error_handler(code))

    @app.get("/health", tags=["infra"], response_model=HealthOutput, summary="Healthcheck")
    def health():
        """Usado pelos healthchecks do Docker e pelas probes do Kubernetes."""
        return {"status": "ok"}

    @app.get("/tasks", tags=["tasks"], response_model=list[TaskOutput], summary="Lista tarefas")
    def list_tasks(
        status: StatusFilter | None = Query(None, description="Filtra por status; omitido = todas."),
    ):
        """Retorna as tarefas na ordem de criação."""
        return service.list_tasks(to_status(status))

    @app.post(
        "/tasks",
        tags=["tasks"],
        response_model=TaskOutput,
        status_code=status.HTTP_201_CREATED,
        responses=INVALID_TASK,
        summary="Cria uma tarefa",
    )
    def create_task(body: TaskInput):
        """A tarefa nasce com status `PENDING`."""
        return service.create_task(body.title, body.description)

    @app.get(
        "/tasks/{task_id}", tags=["tasks"], response_model=TaskOutput, responses=NOT_FOUND,
        summary="Busca uma tarefa",
    )
    def get_task(task_id: uuid.UUID):
        """Retorna a tarefa com o id informado."""
        return service.get_task_by_id(task_id)

    @app.put(
        "/tasks/{task_id}",
        tags=["tasks"],
        response_model=TaskOutput,
        responses={**NOT_FOUND, **INVALID_TASK},
        summary="Edita uma tarefa",
    )
    def edit_task(task_id: uuid.UUID, body: TaskInput):
        """Substitui título e descrição. O status não muda."""
        return service.edit_task(task_id, body.title, body.description)

    @app.post(
        "/tasks/{task_id}/complete", tags=["tasks"], response_model=TaskOutput, responses=NOT_FOUND,
        summary="Conclui uma tarefa",
    )
    def complete_task(task_id: uuid.UUID):
        """Muda o status para `COMPLETED`. Concluir uma tarefa já concluída não é erro."""
        return service.complete_task(task_id)

    @app.delete(
        "/tasks/{task_id}",
        tags=["tasks"],
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        responses=NOT_FOUND,
        summary="Remove uma tarefa",
    )
    def delete_task(task_id: uuid.UUID):
        """Remove definitivamente a tarefa."""
        service.delete_task(task_id)

    return app


def _error_handler(code):
    async def handler(request: Request, error: Exception):
        return JSONResponse(status_code=code, content={"detail": str(error)})
    return handler
