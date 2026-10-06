"""Valida respostas HTTP reais contra docs/openapi.yaml."""
import re
from functools import cache
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

SPEC_FILE = Path(__file__).resolve().parents[3] / "docs" / "openapi.yaml"


@cache
def _spec():
    return yaml.safe_load(SPEC_FILE.read_text())


def _template_for(path: str) -> str:
    path = path.split("?")[0]
    for template in _spec()["paths"]:
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", template) + "$"
        if re.match(pattern, path):
            return template
    raise AssertionError(f"Rota não documentada: {path}")


def assert_matches_spec(method: str, path: str, status: int, body):
    template = _template_for(path)
    responses = _spec()["paths"][template][method.lower()]["responses"]
    assert str(status) in responses, (
        f"{method} {template} respondeu {status}, mas o spec só documenta {sorted(responses)}"
    )

    content = responses[str(status)].get("content")
    if content is None:
        assert body is None, f"{method} {template} {status} não deveria ter corpo"
        return

    # Os $ref apontam para "#/components/...": anexamos components à raiz do schema.
    schema = {**content["application/json"]["schema"], "components": _spec()["components"]}
    errors = sorted(Draft202012Validator(schema).iter_errors(body), key=str)
    assert not errors, f"{method} {template} {status}: " + "; ".join(e.message for e in errors)
