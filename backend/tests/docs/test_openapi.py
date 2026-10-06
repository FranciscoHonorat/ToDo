from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

from api.app import create_app
from application.task_service import TaskService
from persistence.memory_repository import MemoryRepository

SPEC_FILE = Path(__file__).resolve().parents[3] / "docs" / "openapi.yaml"
TASK_ID_OPERATIONS = [
    ("get", "/tasks/{task_id}"),
    ("put", "/tasks/{task_id}"),
    ("delete", "/tasks/{task_id}"),
    ("post", "/tasks/{task_id}/complete"),
]


@pytest.fixture(scope="module")
def spec():
    return create_app(TaskService(MemoryRepository())).openapi()


def schema_ref(response):
    schema = response["content"]["application/json"]["schema"]
    return [option["$ref"] for option in schema.get("anyOf", [schema])]


def test_generated_spec_is_valid_openapi(spec):
    validate(spec)


@pytest.mark.parametrize("method, path", TASK_ID_OPERATIONS)
def test_operations_with_task_id_document_404(spec, method, path):
    response = spec["paths"][path][method]["responses"]["404"]

    assert schema_ref(response) == ["#/components/schemas/ErrorResponse"]


@pytest.mark.parametrize("method, path", [("post", "/tasks"), ("put", "/tasks/{task_id}")])
def test_operations_with_title_document_both_422_shapes(spec, method, path):
    response = spec["paths"][path][method]["responses"]["422"]

    assert schema_ref(response) == [
        "#/components/schemas/ErrorResponse",
        "#/components/schemas/HTTPValidationError",
    ]


def test_every_operation_has_summary_description_and_tag(spec):
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            where = f"{method.upper()} {path}"
            assert operation.get("summary"), where
            assert operation.get("description"), where
            assert operation.get("tags"), where


def test_task_schemas_have_examples(spec):
    schemas = spec["components"]["schemas"]

    assert schemas["TaskInput"].get("examples")
    assert schemas["TaskOutput"].get("examples")


def test_task_status_is_documented_as_enum(spec):
    status = spec["components"]["schemas"]["Status"]

    assert status["enum"] == ["PENDING", "COMPLETED"]


def test_committed_yaml_matches_the_code(spec):
    """Teste de drift: se falhar, rode `make openapi` e versione o arquivo."""
    assert SPEC_FILE.exists(), "docs/openapi.yaml não existe — rode `make openapi`"
    assert yaml.safe_load(SPEC_FILE.read_text()) == spec


def test_committed_yaml_is_valid_openapi():
    validate(yaml.safe_load(SPEC_FILE.read_text()))


def test_operation_ids_are_the_handler_names(spec):
    operation_ids = {op["operationId"] for ops in spec["paths"].values() for op in ops.values()}

    assert operation_ids == {
        "health", "list_tasks", "create_task", "get_task", "edit_task", "complete_task", "delete_task",
    }
