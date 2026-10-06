import uuid
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from domain.status import Status

TASK_EXAMPLE = {
    "id": "3f1c2b9e-8a4d-4c1e-9b7a-2d5e6f708192",
    "title": "Comprar pão",
    "description": "Na padaria da esquina",
    "status": "PENDING",
}


class TaskInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"title": "Comprar pão", "description": "Na padaria da esquina"}]}
    )

    title: str = Field(description="Título da tarefa. Não pode ser vazio nem só espaços.")
    description: str = Field(default="", description="Detalhes opcionais.")


class TaskOutput(BaseModel):
    model_config = ConfigDict(from_attributes=True, json_schema_extra={"examples": [TASK_EXAMPLE]})

    id: uuid.UUID = Field(description="Identificador gerado pelo servidor.")
    title: str
    description: str
    status: Status


class ErrorResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"detail": "Title cannot be empty."}]})

    detail: str = Field(description="Mensagem de erro de regra de negócio.")


class HealthOutput(BaseModel):
    status: str = Field(examples=["ok"])


StatusFilter = Enum("StatusFilter", {status.name: status.value.lower() for status in Status})


def to_status(status_filter: StatusFilter | None) -> Status | None:
    return Status[status_filter.name] if status_filter else None


NOT_FOUND = {404: {"model": ErrorResponse, "description": "Nenhuma tarefa com esse id."}}

INVALID_TASK = {
    422: {
        "description": "Título vazio (`detail` é texto) ou corpo/parâmetros malformados (`detail` é lista).",
        "content": {
            "application/json": {
                "schema": {
                    "anyOf": [
                        {"$ref": "#/components/schemas/ErrorResponse"},
                        {"$ref": "#/components/schemas/HTTPValidationError"},
                    ]
                }
            }
        },
    }
}
