from application.task_service import TaskService
from sinkhole import find_pass_through_methods, public_methods

# Regra 80/20 (Mark Richards): até ~20% de repasses puros é aceitável;
# acima disso a camada de aplicação vira um "ralo" que só encaminha chamadas.
MAX_PASS_THROUGH_RATIO = 0.2


def test_task_service_is_not_an_architecture_sinkhole():
    pass_through = find_pass_through_methods(TaskService, collaborator="repository")
    ratio = len(pass_through) / len(public_methods(TaskService))

    assert ratio <= MAX_PASS_THROUGH_RATIO, (
        f"{ratio:.0%} dos casos de uso só repassam para o repositório: {pass_through}"
    )
