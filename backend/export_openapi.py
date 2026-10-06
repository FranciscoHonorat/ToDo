"""Gera docs/openapi.yaml a partir do código. Uso: python export_openapi.py"""
from pathlib import Path

import yaml

from api.app import create_app
from application.task_service import TaskService
from persistence.memory_repository import MemoryRepository

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"
HEADER = "# Arquivo gerado por backend/export_openapi.py — não edite à mão (rode `make openapi`).\n"


def _str_presenter(dumper, value):
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


yaml.SafeDumper.add_representer(str, _str_presenter)


def main():
    spec = create_app(TaskService(MemoryRepository())).openapi()
    OUTPUT.write_text(HEADER + yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
    print(f"OpenAPI escrito em {OUTPUT}")


if __name__ == "__main__":
    main()
