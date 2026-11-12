# To Do List

[![CI](https://github.com/FranciscoHonorat/ToDo/actions/workflows/ci.yml/badge.svg)](https://github.com/FranciscoHonorat/ToDo/actions/workflows/ci.yml)
[![CodeQL](https://github.com/FranciscoHonorat/ToDo/actions/workflows/codeql.yml/badge.svg)](https://github.com/FranciscoHonorat/ToDo/actions/workflows/codeql.yml)

Aplicação de tarefas desenvolvida com TDD: backend Python em camadas (FastAPI + SQLite) e frontend Vue 3.

```
backend/
  domain/        Task, Status, exceções, contrato TaskRepository (Protocol)
  application/   TaskService (casos de uso) e TaskDTO
  persistence/   MemoryRepository, SqliteRepository, conexão + db/schema.sql
  ui/            CLI (argparse)
  api/           adaptador HTTP (FastAPI)
  composition.py montagem das dependências, usada por main.py (CLI) e server.py (API)
  tests/         unit/ · integration/ (SQLite real, CLI, concorrência) · architecture/ · docs/ · e2e/
frontend/
  e2e/              Playwright (navegador real contra API + frontend)
  src/api/          TaskApi (interface) + implementação HTTP
  src/composables/  useTasks — estado e casos de uso da tela
  src/components/   TaskForm, TaskItem, TaskFilter
  tests/            Vitest + FakeTaskApi em memória
infra/helm/todo/    chart Helm (Kubernetes)
load/               teste de carga (Vegeta + Locust)
docs/openapi.yaml   especificação da API
.github/            CI, CodeQL e Dependabot
```

## Rodando

### Docker Compose

```bash
make up     # http://localhost:8080  (dados no volume todo-data)
make down
```

### Kubernetes (Helm)

```bash
make k8s-up     # cria um cluster kind, carrega as imagens e instala o chart
kubectl --context kind-todo -n todo port-forward svc/todo-frontend 8080:80
make k8s-down
```

Chart em `infra/helm/todo`. O backend usa SQLite num PVC, por isso roda com **1 réplica** e
estratégia `Recreate`; para escalar horizontalmente seria preciso trocar por Postgres
(basta outro repositório implementando `TaskRepository` + os mesmos testes de contrato).

### Local

```bash
make install
make api   # http://localhost:8000  (docs em /docs)
make web   # http://localhost:5173  (o Vite faz proxy de /api para a API)
make cli ARGS="list --status pending"
```

## API e documentação (OpenAPI)

- Especificação versionada: [`docs/openapi.yaml`](docs/openapi.yaml) (OpenAPI 3.1), gerada a partir do código com `make openapi`.
- Swagger UI: http://localhost:8000/docs em desenvolvimento, ou http://localhost:8080/api/docs no compose/k8s
  (lá o backend roda com `API_ROOT_PATH=/api`, atrás do nginx). ReDoc em `/redoc`.
- `backend/tests/docs/test_openapi.py` garante que o YAML é OpenAPI válido, que **não está desatualizado**
  em relação ao código (teste de drift) e que toda rota documenta seus erros (404/422), exemplos e descrições.

| Método | Rota                     | Resposta |
|--------|--------------------------|----------|
| GET    | /health                  | 200 |
| GET    | /tasks?status=pending&limit=50&offset=0 | 200 lista + `X-Total-Count` / 422 status ou paginação inválidos (`limit` 1–1000, opcional) |
| POST   | /tasks                   | 201 tarefa / 422 título vazio ou corpo inválido |
| GET    | /tasks/{id}              | 200 / 404 / 422 id malformado |
| PUT    | /tasks/{id}              | 200 / 404 / 422 |
| POST   | /tasks/{id}/complete     | 200 / 404 / 422 |
| DELETE | /tasks/{id}              | 204 / 404 / 422 |

## Testes

```bash
make test           # tudo
make test-backend   # unit + integração + arquitetura (pytest)
make test-frontend  # type-check + unit + arquitetura (vitest)
make test-arch      # só arquitetura
make test-e2e       # backend: uvicorn real + contrato OpenAPI; frontend: Playwright (API :8001 + Vite :5174)
E2E_BASE_URL=http://localhost:8080 npx playwright test   # E2E contra o compose/cluster (APAGA os dados!)
```

**E2E do backend** (`backend/tests/e2e/`): sobe o uvicorn como processo real, com banco próprio, e
valida **cada resposta contra o `docs/openapi.yaml`** (status documentado + schema do corpo). Cobre a jornada
completa, todos os erros, restart do servidor e requisições concorrentes.

**Testes de arquitetura**
- `backend/pyproject.toml` (`[tool.importlinter]`): camadas `api|ui → application → domain`; o domain não
  importa frameworks; a application não conhece persistência; só a composition root instancia o SQLite.
- `backend/tests/architecture/sinkhole.py`: detecta casos de uso que apenas repassam para o repositório
  (anti-padrão *architecture sinkhole*); o teste falha se passarem de 20% (regra 80/20).
- `frontend/tests/architecture.test.ts`: componentes não importam a API nem composables; só `main.ts`
  conhece a implementação HTTP.

- `backend/tests/test_repository_contract.py` roda os mesmos testes contra as duas implementações de repositório.
- `frontend/tests/fakeTaskApi.ts` é o equivalente do `MemoryRepository` no frontend.

**Lint:** o backend segue o PEP 8, verificado pelo `flake8` (configuração em `backend/.flake8`, linhas de até 120
caracteres). Para rodar: `cd backend && flake8 .`

## CI/CD (GitHub Actions)

Todo push e pull request para `master` dispara os workflows em `.github/workflows/`:

| Workflow | Job | O que faz |
|----------|-----|-----------|
| `ci.yml` | Backend · lint, unit tests | `flake8` + `pytest` (Python 3.14) |
| `ci.yml` | Backend · security checks | `bandit` (análise de segurança, sem a pasta `tests/`) |
| `ci.yml` | Frontend · typecheck, unit tests | `vue-tsc` + `vitest` (Node 24) |
| `codeql.yml` | Analyze (python / javascript-typescript) | análise de segurança do GitHub; roda também todo domingo |

O CI instala apenas o que está em `backend/poetry.lock` e `frontend/package-lock.json`. Se um teste
passa localmente mas falha no CI com `ModuleNotFoundError`, falta o pacote no `backend/pyproject.toml`
(adicione com `poetry add --group dev <pacote>`).

O **Dependabot** (`.github/dependabot.yml`) abre PRs semanais atualizando pip, npm, as imagens base dos
Dockerfiles e as actions. Atualizações minor/patch vêm agrupadas num único PR; as major vêm separadas.

## Teste de carga (Vegeta + Locust)

```bash
make load            # Vegeta (leitura, listagem, escrita) + Locust, cada cenário com servidor e banco próprios
make load-volumes    # a mesma carga com bancos de 0, 1k, 10k e 100k tarefas (≈1 min por volume)
make load-vegeta     # só Vegeta: taxa constante, mede latência honesta (p50/p95/p99)
make load-locust     # só Locust: usuários simulados com fluxo misto (~70% leitura)
make load-ui         # interface web do Locust em http://localhost:8089 (aponta para TARGET ou :8000)

RATE=300 DURATION=30s USERS=100 SPAWN=20 make load    # ajustes
VOLUMES="5000 50000" PENDING_PCT=30 make load         # volumes e proporção de pendentes do seed
LIST_LIMIT=0 make load-volumes                        # listagem sem paginação (como o frontend faz hoje)
TARGET=http://localhost:8080/api make load            # contra o compose (GRAVA dados lá; banco compartilhado)
```

**Estado dos dados é variável do teste.** Cada cenário começa num banco novo populado por `load/seed.py`
com exatamente `VOLUMES` tarefas (gravadas direto no SQLite: 100 mil em menos de 1 s). Os cenários que
escrevem fazem o banco crescer durante a própria rodada, então o script registra **total e pendentes no
início e no fim** de cada cenário (pelo cabeçalho `X-Total-Count`, que também funciona com `TARGET`
externo). O cenário `vegeta list` só lê, então mede a listagem com volume constante.

Os resultados ficam em `load/results/<data-hora>/`: `summary.md` / `summary.csv` (uma linha por volume e
cenário, com p50/p95/p99, vazão, bytes por resposta e as contagens), `counts.csv`, e em `seed-<N>/` os
`vegeta-*.txt|json|html` (relatório, histograma e gráfico) e `locust.html` + CSVs.

**Vegeta × Locust:** o Vegeta dispara numa **taxa fixa** (modelo aberto), mesmo se o servidor ficar lento,
então a latência medida é honesta. O Locust simula **usuários** (modelo fechado): cada um espera a resposta
antes da próxima requisição. O locustfile usa pausa aleatória porque `constant_throughput` sincroniza os
usuários em rajadas, o que criava fila artificial (p50 de 6 ms → 34 ms com a mesma vazão).

Numa medição de referência (notebook, 8 CPUs, 1 worker uvicorn), a escrita satura primeiro (~570/s), mas a leitura satura logo depois (~635/s): o gargalo atual é **um
processo Python**, não o SQLite. Mais workers do uvicorn ajudariam a leitura, mas não a escrita: cada
worker abriria sua própria conexão e o SQLite continua aceitando um escritor por vez. Para escalar escrita,
o caminho é Postgres.
