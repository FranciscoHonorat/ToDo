"""Cenário de usuários para o Locust.

Cada usuário simulado cria algumas tarefas e depois navega: lista muito,
abre tarefas, edita e conclui de vez em quando. Os pesos de @task definem
a proporção de cada ação (aqui ~70% leitura, ~30% escrita).
"""
import random

from locust import HttpUser, between, task


class TodoUser(HttpUser):
    # Pausa aleatória (média 0,5 s => ~2 req/s por usuário; -u 50 => ~100 req/s).
    # Não use constant_throughput aqui: ele sincroniza os usuários, que passam a
    # chegar em rajadas e criam fila artificial (medimos: p50 de 6 ms -> 34 ms).
    wait_time = between(0.2, 0.8)

    def on_start(self):
        self.task_ids = [self._create() for _ in range(3)]

    def _create(self):
        with self.client.post(
            "/tasks", json={"title": "carga", "description": "locust"}, catch_response=True
        ) as response:
            if response.status_code != 201:
                response.failure(f"esperava 201, veio {response.status_code}")
                return None
            return response.json()["id"]

    def _some_task(self):
        ids = [task_id for task_id in self.task_ids if task_id]
        return random.choice(ids) if ids else None

    @task(4)
    def list_pending(self):
        self.client.get("/tasks?status=pending", name="/tasks?status=pending")

    @task(3)
    def get_task(self):
        if task_id := self._some_task():
            self.client.get(f"/tasks/{task_id}", name="/tasks/{id}")

    @task(2)
    def create_task(self):
        self.task_ids.append(self._create())

    @task(1)
    def edit_task(self):
        if task_id := self._some_task():
            self.client.put(
                f"/tasks/{task_id}", json={"title": "editada", "description": ""}, name="/tasks/{id}"
            )

    @task(1)
    def complete_task(self):
        if task_id := self._some_task():
            self.client.post(f"/tasks/{task_id}/complete", name="/tasks/{id}/complete")
