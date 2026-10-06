"""Detector do anti-padrão "architecture sinkhole".

Um método é um repasse puro quando seu corpo (ignorando docstring) é uma única
chamada `self.<colaborador>.<metodo>(...)` que recebe exatamente os mesmos
parâmetros do método, na mesma ordem — ou seja, a camada não acrescenta nada.
"""
import ast
import inspect
import textwrap


def public_methods(cls) -> list[str]:
    return sorted(
        name
        for name, member in vars(cls).items()
        if inspect.isfunction(member) and not name.startswith("_")
    )


def find_pass_through_methods(cls, collaborator: str) -> list[str]:
    return [
        name
        for name in public_methods(cls)
        if _is_pass_through(_function_node(getattr(cls, name)), collaborator)
    ]


def _function_node(function) -> ast.FunctionDef:
    source = textwrap.dedent(inspect.getsource(function))
    return ast.parse(source).body[0]


def _is_pass_through(node: ast.FunctionDef, collaborator: str) -> bool:
    body = [statement for statement in node.body if not _is_docstring(statement)]
    if len(body) != 1 or not isinstance(body[0], (ast.Return, ast.Expr)):
        return False

    call = body[0].value
    if not (isinstance(call, ast.Call) and _is_collaborator_method(call.func, collaborator)):
        return False

    parameters = [argument.arg for argument in node.args.args[1:]]
    forwarded = [argument.id for argument in call.args if isinstance(argument, ast.Name)]
    return len(forwarded) == len(call.args) and not call.keywords and forwarded == parameters


def _is_collaborator_method(func: ast.expr, collaborator: str) -> bool:
    return (
        isinstance(func, ast.Attribute)
        and isinstance(func.value, ast.Attribute)
        and func.value.attr == collaborator
        and isinstance(func.value.value, ast.Name)
        and func.value.value.id == "self"
    )


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )
