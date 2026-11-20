# Observabilidade DevSecOps: plano de implementação

> **Modo de execução: tutoria.** O usuário escreve todo o código; Claude explica o conceito
> (com exemplo fora do projeto), propõe o teste que falha, revisa e roda os gates
> (CLAUDE.md do usuário). Nada de subagente implementando. Passos com checkbox (`- [ ]`).

**Goal:** traces, métricas e logs do ToDo via OpenTelemetry → Collector → Tempo/Prometheus/Loki
→ Grafana, conduzidos por práticas DevSecOps, em profundidade máxima.

**Architecture:** o backend configura o SDK à mão em `backend/telemetry.py` (composition root)
e exporta OTLP/HTTP para um Collector na rede interna do Compose; o Collector distribui para os
backends. Segurança entra em cada módulo como gate automático (teste, policy, scan) no
`make lint`, no pre-commit e no CI.

**Tech Stack:** Python 3.14, FastAPI, Poetry 2.3.2; opentelemetry-sdk 1.45.x,
opentelemetry-instrumentation-fastapi 0.66bX, opentelemetry-exporter-otlp-proto-http 1.45.x
(versões conferidas em 2026-11-12, reconferir ao instalar); OTel Collector contrib; Grafana
Tempo, Prometheus, Loki, Grafana; gitleaks; Trivy.

**Spec:** `docs/specs/2026-11-12-observability-design.md`

**Como este plano está dividido:** os módulos 0–2 estão detalhados passo a passo. Os módulos
3–14 estão como roteiro (entregável, gates, decisões já tomadas) e ganham um plano detalhado
próprio (`docs/plans/…-observability-mN.md`) quando chegarmos neles: o que o
usuário aprender e as versões do momento mudam os detalhes, e detalhar agora geraria um plano
desatualizado.

## Global Constraints

- `domain/` e `application/` nunca importam `opentelemetry` (contrato do import-linter).
- Sem `OTEL_EXPORTER_OTLP_ENDPOINT`: nenhum exporter de rede; testes e CLI rodam sem Collector.
- Título e descrição de tarefa nunca em span, evento, log, label de métrica ou exemplar.
- Nenhum atributo/label com id de tarefa, título ou URL com id em **métricas** (cardinalidade).
- Só o Grafana publicado no host, em `127.0.0.1`; Collector, Tempo, Prometheus e Loki só em
  rede interna.
- Todo container novo: não-root, `read_only: true`, `cap_drop: [ALL]`,
  `security_opt: [no-new-privileges:true]`, limites de CPU/memória, imagem fixada por digest.
- Nenhum segredo no git; segredos via arquivo ignorado + Docker secrets.
- Toda action nova no CI fixada por **SHA de commit**, não por tag.
- Gates locais = gates do CI (`make lint`, pre-commit e CI rodam as mesmas ferramentas).
- Mudanças em `master` só por PR (ruleset). Trabalho no branch `feat/observability`.
- O usuário faz os commits (Claude não commita).

## Review Focus

1. **Query string com dado do usuário no span:** o instrumentador grava `http.url` com a query
   inteira por padrão. Hoje a API só tem `status/limit/offset`, mas um parâmetro novo vazaria.
   → Task 1.5 testa com um valor-marcador na query e no corpo.
2. **Collector fora do ar:** o backend deve continuar respondendo 2xx normalmente (exporter
   em lote, falha só em log). → Task 1.8 Step 6 derruba o Collector e roda `make load`.
3. **Mensagem de exceção com dado do usuário:** `record_exception` copia a mensagem para o
   span. → Task 1.5 inclui o caminho de erro 422 com o marcador no título.
4. **Grafana sem senha configurada:** sem o arquivo de segredo, o Grafana não pode subir com
   `admin/admin`. → Task 2.3 faz a subida falhar sem o segredo.
5. **Testes que vazam estado global do OTel:** `set_tracer_provider` só funciona uma vez por
   processo; testes devem usar providers locais. → Task 1.3 proíbe provider global nos testes.

---

## Módulo 0: Fundamentos e ameaças

### Task 0.1: Modelo de ameaças da stack de observabilidade

**Files:**
- Create: `docs/security/threat-model-observability.md`

- [ ] **Step 1:** Aula: sinais (trace/métrica/log), API × SDK, Collector, OTLP; STRIDE e
  fronteiras de confiança.
- [ ] **Step 2:** Usuário desenha o diagrama de fluxo de dados (texto/mermaid) com as
  fronteiras: navegador | nginx | backend | rede de observabilidade | host (Grafana).
- [ ] **Step 3:** Usuário preenche a tabela STRIDE: `ameaça | componente | impacto |
  mitigação | módulo que implementa | gate que verifica`. Mínimo obrigatório: vazamento de
  dado sensível em telemetria, Collector exposto, Grafana com senha padrão, log injection,
  inundação de telemetria (DoS/cardinalidade), imagem com CVE, segredo no git, API sem
  autenticação (risco aceito, próximo projeto).
- [ ] **Step 4:** Revisão: cada linha tem um gate verificável ou está marcada "risco aceito".
- [ ] **Step 5:** Commit `docs(security): threat model for the observability stack`.

### Task 0.2: ADR da arquitetura

**Files:**
- Create: `docs/adr/0001-observability-architecture.md` (Contexto / Decisão / Alternativas /
  Consequências)

- [ ] **Step 1:** Usuário escreve o ADR: SDK à mão (A) × auto-instrumentação × prometheus_client
  × otel-lgtm; Prometheus em pull; Collector como única porta de entrada.
- [ ] **Step 2:** Revisão e commit `docs(adr): observability architecture`.

### Task 0.3: gitleaks no pre-commit e no CI

**Files:**
- Modify: `.pre-commit-config.yaml` (novo repo `https://github.com/gitleaks/gitleaks`, hook
  `gitleaks`, `rev` = última release conferida)
- Modify: `.github/workflows/ci.yml` (job `secrets`: checkout com `fetch-depth: 0` + gitleaks
  fixado por SHA ou binário de release com checksum conferido)
- Create: `.gitleaks.toml` só se houver falso positivo real (YAGNI)

- [ ] **Step 1 (erro provocado):** criar `tmp-leak.txt` com uma chave falsa no formato AWS
  (`AKIA` + 16 caracteres) e rodar `pre-commit run gitleaks --files tmp-leak.txt`.
  Esperado antes do hook: nada acontece (o hook não existe).
- [ ] **Step 2:** Usuário adiciona o hook. Rodar de novo. Esperado: **Failed**, com o achado
  `aws-access-token`. Ler a saída inteira.
- [ ] **Step 3:** Apagar `tmp-leak.txt`. `pre-commit run gitleaks --all-files` → Passed.
- [ ] **Step 4:** Usuário escreve o job do CI. Verificação: o PR mostra o job `secrets` verde.
- [ ] **Step 5:** Commit `ci(security): scan for secrets with gitleaks`.

---

## Módulo 1: Traces no backend

### Task 1.1: Dependências e contrato de camadas

**Files:**
- Modify: `backend/pyproject.toml` (grupo principal: `opentelemetry-api`, `opentelemetry-sdk`,
  `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp-proto-http`; contratos)
- Modify: `backend/poetry.lock` (via `poetry add`)

- [ ] **Step 1 (erro provocado):** adicionar `"opentelemetry"` aos `forbidden_modules` dos
  contratos "Domain é puro" e "Application depende só do domain"; criar temporariamente
  `import opentelemetry` em `application/task_service.py`; `.venv/bin/lint-imports`.
  Esperado: contrato **BROKEN** apontando a linha. (Antes do `poetry add` o import falha:
  instalar primeiro.)
- [ ] **Step 2:** Remover o import temporário. `make lint-backend` → verde.
- [ ] **Step 3:** Commit `build(backend): add OpenTelemetry SDK and forbid it in inner layers`.

### Task 1.2: Testes de aprendizado do SDK

Testes que documentam como a biblioteca se comporta (não testam o nosso código).

**Files:**
- Create: `backend/tests/learning/test_otel_sdk.py`

- [ ] **Step 1:** Usuário escreve, um por vez, prevendo o resultado antes de rodar:
  - `test_resource_attributes_in_code_override_otel_service_name_env` — com
    `OTEL_SERVICE_NAME=from-env` (monkeypatch), `Resource.create({"service.name": "from-code"})`
    → `"from-code"`.
  - `test_resource_without_service_name_reads_env` — `Resource.create({})` → `"from-env"`.
  - `test_span_context_does_not_cross_a_plain_thread` — span ativo; dentro de
    `threading.Thread`, `trace.get_current_span()` não é o span; com
    `contextvars.copy_context().run(...)` é.
  - `test_batch_processor_exports_only_on_flush` — `BatchSpanProcessor(InMemorySpanExporter())`
    com `schedule_delay_millis=60_000`: 0 spans antes, 1 depois de `force_flush()`.
  - `test_tracer_provider_registers_shutdown_on_exit_by_default` — assinatura de
    `TracerProvider` tem `shutdown_on_exit=True` (ler a fonte do SDK junto).
- [ ] **Step 2:** `poetry run pytest tests/learning -v` → todos PASS; discutir cada previsão errada.
- [ ] **Step 3:** Commit `test(learning): pin OpenTelemetry SDK behaviors we rely on`.

### Task 1.3: `build_resource` e `build_tracer_provider`

**Files:**
- Create: `backend/telemetry.py`
- Test: `backend/tests/unit/test_telemetry.py`

**Interfaces:**
- Produces:
  - `build_resource(environ: Mapping[str, str]) -> Resource` — `service.name` =
    `environ.get("OTEL_SERVICE_NAME", "todo-backend")`, `service.version` =
    `environ.get("TODO_VERSION", "dev")`, `deployment.environment.name` =
    `environ.get("TODO_ENVIRONMENT", "local")`.
  - `span_processors(environ: Mapping[str, str]) -> list[SpanProcessor]` — `[]` sem
    `OTEL_EXPORTER_OTLP_ENDPOINT`; senão `[BatchSpanProcessor(OTLPSpanExporter())]` (o exporter
    lê endpoint e headers do ambiente).
  - `build_tracer_provider(resource: Resource, processors: Sequence[SpanProcessor]) -> TracerProvider`

- [ ] **Step 1: testes que falham** (um por vez, ciclo red/green completo em cada):
  - `test_resource_defaults_identify_the_service` — `build_resource({})` →
    `service.name == "todo-backend"`, `service.version == "dev"`,
    `deployment.environment.name == "local"`.
  - `test_resource_reads_service_name_from_env` — `{"OTEL_SERVICE_NAME": "x"}` → `"x"`.
  - `test_no_endpoint_means_no_exporters` — `span_processors({}) == []`.
  - `test_endpoint_configures_a_batch_otlp_exporter` — com endpoint, 1 processor do tipo
    `BatchSpanProcessor`.
  - `test_tracer_provider_records_spans_with_the_resource` — provider com
    `SimpleSpanProcessor(InMemorySpanExporter())`; span "x" exportado com o `service.name`.
- [ ] **Step 2:** Rodar cada um e ver falhar (`ModuleNotFoundError`, depois `AttributeError`…).
- [ ] **Step 3:** Usuário implementa em `backend/telemetry.py`. Regra: **nenhum teste chama
  `trace.set_tracer_provider`** (estado global, só uma vez por processo).
- [ ] **Step 4:** `poetry run pytest tests/unit/test_telemetry.py -v` → PASS; `make lint-backend` verde.
- [ ] **Step 5:** Commit `feat(telemetry): build resource and tracer provider from environment`.

### Task 1.4: Spans HTTP com `FastAPIInstrumentor`

**Files:**
- Modify: `backend/telemetry.py`
- Test: `backend/tests/unit/test_telemetry_http.py` (fixture `traced_client`: app com
  `MemoryRepository`, provider local + `InMemorySpanExporter`; `uninstrument_app` no teardown)

**Interfaces:**
- Consumes: `build_tracer_provider` (1.3), `api.app.create_app(service, root_path="")`.
- Produces: `instrument_app(app: FastAPI, tracer_provider: TracerProvider) -> None` — chama
  `FastAPIInstrumentor.instrument_app(app, tracer_provider=..., exclude_spans=["receive", "send"],
  excluded_urls="health")`.

- [ ] **Step 1: testes que falham:**
  - `test_request_produces_one_server_span_named_by_route` — `GET /tasks` → exatamente 1 span,
    `kind == SpanKind.SERVER`, `name == "GET /tasks"`, `attributes["http.route"] == "/tasks"`.
  - `test_route_template_not_raw_path` — `GET /tasks/{id}` com id real →
    `name == "GET /tasks/{task_id}"` (nome de baixa cardinalidade).
  - `test_health_is_not_traced` — `GET /health` → 0 spans.
- [ ] **Step 2:** Ver falhar; usuário implementa; ver passar.
- [ ] **Step 3 (aula):** rodar com `OTEL_SEMCONV_STABILITY_OPT_IN=http` e comparar os atributos
  (`http.status_code` → `http.response.status_code`, `http.url` → `url.*`). Decisão do usuário,
  registrada no ADR 0001: adotar as convenções estáveis (`http`) ou não. Se adotar, o env entra
  em compose e nos testes ajustam os nomes.
- [ ] **Step 4:** Commit `feat(telemetry): trace HTTP requests by route`.

### Task 1.5: Gate de dado sensível (barreira 1)

**Files:**
- Test: `backend/tests/security/test_no_sensitive_data_in_telemetry.py`
- Create: `backend/tests/security/telemetry_dump.py` — `all_strings(spans) -> list[str]`: nomes,
  valores de atributos, eventos e atributos de eventos, recursivamente.

**Interfaces:**
- Consumes: fixture `traced_client` (1.4; mover para `tests/conftest.py` ou
  `tests/telemetry_fixtures.py` se for compartilhada).

- [ ] **Step 1:** Teste `test_task_content_never_reaches_spans`: `MARKER = "SENSITIVE-7f3a"`;
  criar tarefa com título e descrição contendo o marcador, editar, listar, buscar por id,
  enviar `GET /tasks?status=pending&q=SENSITIVE-7f3a` e um `POST` com título só de espaços +
  marcador na descrição (caminho 422). Assert: `MARKER` não aparece em nenhuma string do dump.
- [ ] **Step 2:** Rodar. Esperado: **FAIL** pelo `http.url` com `q=SENSITIVE-7f3a` (Review
  Focus 1). Ler qual atributo vazou.
- [ ] **Step 3:** Usuário decide a correção e explica por quê; opções a discutir: convenções
  estáveis + `url.query` redigida, ou `server_request_hook` que remove a query do span.
  Ver passar.
- [ ] **Step 4 (erro provocado):** usuário adiciona temporariamente
  `span.set_attribute("task.title", ...)` num handler; o teste deve falhar; remover.
- [ ] **Step 5:** Incluir `tests/security` no `pytest` padrão (já é coletado) e no
  modelo de ameaças (coluna "gate").
- [ ] **Step 6:** Commit `test(security): fail when task content leaks into traces`.

### Task 1.6: Ligar no servidor

**Files:**
- Modify: `backend/server.py`
- Test: `backend/tests/integration/test_server_telemetry.py`

**Interfaces:**
- Consumes: `build_resource`, `span_processors`, `build_tracer_provider`, `instrument_app`.
- Produces: `setup_telemetry(app: FastAPI, environ: Mapping[str, str]) -> TracerProvider` em
  `telemetry.py` — monta, registra global (`trace.set_tracer_provider`) e instrumenta. Só
  `server.py` chama.

- [ ] **Step 1:** Teste em subprocesso (estado global isolado):
  `test_server_starts_without_collector` — importar `server` sem
  `OTEL_EXPORTER_OTLP_ENDPOINT` e fazer `GET /health` via TestClient → 200, sem erro de rede.
- [ ] **Step 2:** Usuário implementa `setup_telemetry` e chama em `server.py`.
- [ ] **Step 3:** `make test-backend` → tudo verde (inclusive e2e).
- [ ] **Step 4:** Commit `feat(telemetry): enable tracing in the API server`.

### Task 1.7: Aula: auto-instrumentação (comparação, sem commit)

- [ ] Rodar `opentelemetry-instrument --traces_exporter console uvicorn server:app` com uma
  app sem `setup_telemetry` (branch descartável); comparar spans; anotar diferenças no ADR 0001.
- [ ] Mesma comparação com a configuração declarativa do SDK (arquivo YAML via
  `OTEL_EXPERIMENTAL_CONFIG_FILE` ou o nome vigente; conferir o estado de estabilidade na versão
  instalada antes da aula).

### Task 1.8: Collector no Compose (exporter `debug`)

**Files:**
- Create: `infra/observability/otel-collector.yaml` — receiver `otlp` só HTTP em
  `0.0.0.0:4318`; processors `memory_limiter` (`check_interval: 1s`, `limit_percentage: 80`,
  `spike_limit_percentage: 20`) e `batch`; exporter `debug` (`verbosity: detailed`); pipeline
  `traces`; extension `health_check`.
- Modify: `docker-compose.yml` — serviço `otel-collector` (imagem contrib por digest; sem
  `ports:`; hardening da Global Constraints); redes `app` e `observability`
  (`internal: true`); backend nas duas, com
  `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`.
- Modify: `Makefile` — alvo `lint-infra` ganha `otelcol-contrib validate` via `docker run` da
  mesma imagem.

- [ ] **Step 1 (erro provocado):** escrever a config com um processor não declarado no
  pipeline; rodar o validate; ler o erro; corrigir.
- [ ] **Step 2:** `make up`; `curl -s localhost:8080/api/tasks`;
  `docker compose logs otel-collector | grep "GET /tasks"` → aparece o span com `service.name`.
- [ ] **Step 3:** Segurança: `docker compose port otel-collector 4318` → sem porta publicada;
  `curl localhost:4318` do host → conexão recusada.
- [ ] **Step 4:** `docker compose exec otel-collector id` (se a imagem tiver shell; senão
  `docker inspect`) → uid ≠ 0.
- [ ] **Step 5:** Resiliência (Review Focus 2): `docker compose stop otel-collector`;
  `TARGET=http://localhost:8080/api make load-vegeta` → 0% de falhas na API.
- [ ] **Step 6:** Commit `feat(infra): OpenTelemetry Collector receiving traces`.

---

## Módulo 2: Tempo + Grafana com hardening

### Task 2.1: Policy-as-code do Compose

**Files:**
- Create: `infra/policy/test_compose_policy.py` (pytest + pyyaml do grupo dev; rodado por
  `make lint-infra` e pelo CI)

- [ ] **Step 1: testes que falham** (parametrizados por serviço de `docker-compose.yml`):
  - `test_service_runs_as_non_root` — `user` definido e ≠ `0`/`root`, ou serviço listado em
    `NON_ROOT_BY_IMAGE` com a prova (uid da imagem) num comentário.
  - `test_service_is_hardened` — `read_only: true`, `cap_drop` contém `ALL`,
    `no-new-privileges:true` em `security_opt`.
  - `test_service_has_resource_limits` — `deploy.resources.limits.memory` e `.cpus`.
  - `test_image_is_pinned_by_digest` — imagens de terceiros contêm `@sha256:`.
  - `test_only_grafana_and_frontend_publish_ports_and_only_on_loopback` — `ports` só em
    `grafana` (`127.0.0.1:`) e `frontend`.
- [ ] **Step 2:** Rodar → falhas em `backend`, `frontend`, `otel-collector`. Ler cada uma.
- [ ] **Step 3:** Usuário endurece os serviços existentes (`tmpfs` onde precisar escrever;
  o frontend passa a publicar só em `127.0.0.1:8080`). Ver passar; `make up` + E2E verdes.
- [ ] **Step 4:** Commit `test(infra): enforce container hardening policy for compose`.

### Task 2.2: Tempo

**Files:**
- Create: `infra/observability/tempo.yaml` (receiver OTLP gRPC interno, storage local em volume,
  retenção explícita)
- Modify: `infra/observability/otel-collector.yaml` (exporter `otlp/tempo` → `tempo:4317`;
  `tls.insecure: true` só na rede interna, com comentário apontando o módulo 14 para mTLS)
- Modify: `docker-compose.yml` (serviço `tempo`, rede `observability`, volume)

- [ ] **Step 1:** Policy (2.1) falha para `tempo` até ele estar endurecido; endurecer.
- [ ] **Step 2:** `make up`, gerar tráfego; `docker compose logs tempo` sem erros de ingestão.
  A verificação visual do trace fica para a 2.3 (Grafana).
- [ ] **Step 3:** Commit `feat(infra): store traces in Tempo`.

### Task 2.3: Grafana endurecido com datasource Tempo

**Files:**
- Create: `infra/observability/grafana/provisioning/datasources/datasources.yaml` (Tempo,
  `editable: false`)
- Modify: `docker-compose.yml` (serviço `grafana`: `127.0.0.1:3000:3000`; secret
  `grafana_admin_password`; env `GF_SECURITY_ADMIN_PASSWORD__FILE`,
  `GF_AUTH_ANONYMOUS_ENABLED=false`, `GF_USERS_ALLOW_SIGN_UP=false`,
  `GF_ANALYTICS_REPORTING_ENABLED=false`, `GF_SECURITY_DISABLE_GRAVATAR=true`)
- Modify: `.gitignore` (`infra/observability/secrets/`)
- Modify: `Makefile` (alvo `secrets` gera a senha com `openssl rand -base64 32`, `chmod 600`;
  `up` depende dele)

- [ ] **Step 1 (Review Focus 4):** sem o arquivo de segredo, `docker compose up grafana` deve
  **falhar** (secret ausente). Conferir.
- [ ] **Step 2:** `make secrets && make up`; login com `admin` + senha gerada; `admin/admin`
  recusado; aba anônima sem acesso.
- [ ] **Step 3:** Explore → Tempo → achar o trace de `GET /tasks`; ler o span. Aula de TraceQL:
  `{ span.http.route = "/tasks/{task_id}" && duration > 5ms }`.
- [ ] **Step 3b:** Menor privilégio: criar um usuário `viewer` (papel Viewer) e confirmar que
  ele não edita datasources nem dashboards.
- [ ] **Step 4:** `gitleaks` e policy verdes; `git status` não mostra a pasta `secrets/`.
- [ ] **Step 5:** Commit `feat(infra): Grafana with Tempo datasource, hardened`.

### Task 2.4: Trivy no CI

**Files:**
- Modify: `.github/workflows/ci.yml` (job `supply-chain`: build das imagens do app; scan das
  imagens do app e das de terceiros do compose, `severity: HIGH,CRITICAL`, `ignore-unfixed`,
  `exit-code: 1`; scan de config dos Dockerfiles e do chart Helm)
- Create: `.trivyignore` só com CVE justificado e data de revisão (se necessário)

- [ ] **Step 1:** Antes de escolher o mecanismo, conferir avisos de segurança recentes sobre a
  `aquasecurity/trivy-action` e o próprio Trivy; usar SHA de commit verificado ou binário de
  release com checksum. Registrar a escolha no ADR.
- [ ] **Step 2:** Rodar localmente `trivy image` numa imagem e `trivy config backend/` e ler o
  relatório antes de escrever o job.
- [ ] **Step 3:** Job no CI; PR mostra o job verde (ou o achado tratado).
- [ ] **Step 4:** Commit `ci(security): scan images and configs with Trivy`.

---

## Módulos 3–14 (roteiro; cada um ganha plano detalhado ao começar)

| Mód. | Entregável | Gates novos | Já decidido |
|---|---|---|---|
| 3 | Span manual no `SqliteRepository` (`db.system.name=sqlite`, operação, sem valores); OTel web no Vue; `traceparent` passando pelo nginx; rota OTLP só de traces no nginx com limite de corpo | teste em memória do span do repositório; barreira 1 estendida ao span do banco; E2E Playwright verifica um trace com span do navegador e do SQLite | span manual (não o instrumentador sqlite3); navegador nunca fala direto com o Collector |
| 4 | `MeterProvider`; contador `todo.tasks.created` no `api/`; métricas HTTP; runtime; Views (buckets, atributos permitidos); exporter `prometheus` no Collector; Prometheus raspando; PromQL | teste com `InMemoryMetricReader`; teste de cardinalidade (atributos permitidos); `promtool check config` | pull; métrica de negócio no adaptador |
| 5 | Exemplars; links métrica → trace, trace → logs, log → trace nos datasources | teste de exemplar presente no histograma | — |
| 6 | `logging` + `LoggingHandler`; logs estruturados; Loki (OTLP nativo) com `limits_config` e retenção; LogQL | teste CWE-117 (quebra de linha no título não cria log falso); barreira 1 para logs; validação da config do Loki | — |
| 7 | Pipeline resiliente (filas, retry); processor de redação (barreira 2) com OTTL; telemetria do Collector; Collector próprio com `ocb` | teste de redação no Collector (enviar OTLP com marcador, verificar saída); SBOM menor que a contrib | redação também no Collector |
| 8 | Head sampling `ParentBased` + ratio; `tail_sampling` (erros + lentas) | medição de volume com e sem amostragem | — |
| 9 | SLIs como recording rules; SLO; burn rate multijanela; Alertmanager com webhook local; runbooks | `promtool test rules` no CI; todo alerta tem `runbook_url` (policy) | — |
| 10 | Regras de detecção (pico de 4xx/422, varredura de ids com 404, taxa anormal, falha de login no Grafana) | `promtool test rules`; runbook por regra | pronto para sinais de autenticação futuros |
| 11 | `make load` com/sem OTel e por taxa de amostragem; relatório | — | medir antes de afirmar |
| 12 | Game day: derrubar Loki/Collector, inundar, config quebrada; postmortem | alerta certo dispara (verificado) | sem culpa |
| 13 | SBOM das imagens; Dependabot para digests do compose; verificação de assinatura onde houver; revisão de todos os gates | CI completo bloqueante | — |
| 14 | kind: charts, mTLS app ↔ Collector, auth nos receivers, NetworkPolicy, Pod Security `restricted` | policy de manifests | Compose antes, kind depois |
