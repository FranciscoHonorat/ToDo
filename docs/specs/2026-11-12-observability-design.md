# Observabilidade do ToDo com práticas DevSecOps

Data: 2026-11-12 · Status: rascunho para aprovação

## Intenção

Adicionar traces, métricas e logs ao ToDo com OpenTelemetry, Collector, Tempo, Prometheus,
Loki e Grafana, **conduzido pelas práticas da cultura DevSecOps**: segurança desde o primeiro
passo (shift-left), tudo como código, gates automáticos no CI, menor privilégio, e ciclos de
feedback (alertas → runbook → game day → postmortem). A observabilidade serve à operação
**e** à detecção de segurança.

O objetivo é **aprender com profundidade máxima**; qualidade e segurança acima de velocidade.
O usuário escreve o código, em passos pequenos (conceito → teste que falha → código do
usuário → revisão), conforme o CLAUDE.md. Fases: **Compose primeiro, kind depois**.

## Princípios DevSecOps aplicados (valem para todos os módulos)

1. **Ameaça antes de código:** cada módulo começa revendo o modelo de ameaças da parte nova.
2. **Shift-left:** o que pode ser verificado localmente roda no pre-commit e no `make lint`;
   o mesmo roda no CI (sem divergência entre a máquina e o CI).
3. **Tudo como código, tudo verificado:** configs do Collector/Prometheus/Loki/Tempo,
   datasources, dashboards, regras de alerta e políticas ficam no git e são validados no CI.
4. **Gates que falham o build:** vazamento de dado sensível, segredo no repositório,
   vulnerabilidade alta/crítica, config insegura, regra de alerta sem teste.
5. **Menor privilégio e defesa em profundidade:** nada exposto sem necessidade, nada como root,
   duas barreiras para dados sensíveis (no app e no Collector).
6. **Feedback e aprendizado sem culpa:** todo alerta tem runbook; falhas são provocadas em
   game days; cada game day gera um postmortem curto.
7. **Medir antes de afirmar:** custo da instrumentação medido com `make load`.

## Metas

### Observabilidade
- Três sinais via OTLP → Collector → Tempo / Prometheus (scrape) / Loki.
- Propagação W3C (`traceparent`) do **frontend** (navegador) até o span do SQLite: um trace
  de ponta a ponta.
- Métricas a fundo: tipos de instrumento, temporalidade, histogramas (explícitos e
  exponenciais), **exemplars** (métrica → trace), **Views** para cardinalidade, convenções
  semânticas, métricas de runtime.
- Logs estruturados com `trace_id`/`span_id`; correlação log ↔ trace ↔ métrica no Grafana.
- Amostragem: head (`ParentBased` + ratio) no app e **tail sampling** no Collector
  (manter erros e lentas).
- Pipeline resiliente: `memory_limiter`, `batch`, filas/retry; telemetria do próprio Collector.
- SLI/SLO da API com error budget e alertas de **burn rate** multijanela (Prometheus rules +
  Alertmanager), com `promtool test rules`; **recording rules** para os SLIs.
- **Por dentro do SDK:** como o contexto vive em `contextvars` (e por que threads/async
  importam), `SpanProcessor` (escrever um próprio), propagators, ciclo de vida e `shutdown`
  (flush ao encerrar), configuração declarativa do SDK (arquivo YAML) comparada ao código.
- **Linguagens de consulta:** PromQL (rate, histogram_quantile, agregações), LogQL (filtros,
  parsers, métricas a partir de logs), TraceQL (buscar spans por atributo e duração), OTTL
  (transformar dados no Collector).
- **Collector próprio com o OpenTelemetry Collector Builder (ocb):** distribuição só com os
  componentes usados. Menos código = menor superfície de ataque e SBOM menor (DevSecOps).

### Segurança (Sec)
- **Modelo de ameaças** (STRIDE) da stack de observabilidade, versionado.
- **Dados sensíveis:** título/descrição de tarefa nunca em span, log, label ou exemplar.
  Barreira 1: teste no backend que falha se aparecerem. Barreira 2: processor de redação no
  Collector, com teste. Mensagens de exceção tratadas antes de ir para spans.
- **Log injection (CWE-117):** logs estruturados; entrada do usuário nunca forma a mensagem.
- **Segredos:** nenhum no git (senha do Grafana etc. via secrets/arquivo ignorado);
  **gitleaks** no pre-commit e no CI.
- **Rede:** redes separadas no Compose (app × observabilidade); só o Grafana publicado, em
  `127.0.0.1`; Collector só na rede interna.
- **Grafana:** sem `admin/admin`, sem anônimo, sem cadastro, datasources somente leitura,
  papéis mínimos.
- **Containers:** não-root, `read_only`, `cap_drop: [ALL]`, `no-new-privileges`, limites de
  CPU/memória, imagens fixadas por **digest**.
- **Cadeia de suprimentos:** scan de imagens e de configs (Trivy) com gate no CI, **SBOM**
  das imagens, Dependabot atualizando digests; verificação de assinatura onde o fornecedor
  assina (conferir na implementação).
- **Proteção contra excesso:** limites de cardinalidade, `limits_config` e retenção no Loki,
  `memory_limiter` no Collector.
- **Detecção como código:** regras de alerta para padrões suspeitos que a API permite ver
  hoje (pico de 4xx/422, varredura de ids com muitos 404, taxa anormal de requisições,
  falhas de login no Grafana), cada uma com teste e runbook.
- **Fase kind:** TLS/mTLS app ↔ Collector, autenticação nos receivers, NetworkPolicy,
  Pod Security Standards (`restricted`).

### Qualidade
- Validação de configs no CI: `otelcol validate`, `promtool check config|rules`,
  `promtool test rules`, validação de Loki/Tempo, Trivy config.
- Dashboards (RED e SLO) e alertas provisionados como código.
- Custo da instrumentação medido com `make load` (p50/p99/vazão com e sem OTel, e por
  taxa de amostragem), resultados no relatório.
- ADRs das decisões principais; runbook por alerta; postmortem por game day.
- Import-linter: `domain` e `application` não importam `opentelemetry`.

## Não-metas

- Autenticação/autorização na própria API do ToDo (não existe hoje; mudaria o produto).
  A detecção usa só o que a API já expõe. Fica registrado como risco no modelo de ameaças
  e como **próximo projeto**; o módulo de detecção é desenhado para receber sinais de login
  e auditoria quando a autenticação existir. *Minha escolha.*
- Profiling contínuo, SIEM externo, retenção de longo prazo/HA dos backends.
- Métricas DORA (podem virar um módulo depois).

## Anti-metas

- Claude escrever a instrumentação pelo usuário.
- App ou testes dependerem do Collector: sem endpoint, a telemetria é no-op.
- Telemetria virar canal de vazamento de dados ou porta de entrada (backend exposto no host).
- Segurança "no fim": nenhum módulo é concluído com gate de segurança pendente.
- Labels de alta cardinalidade.

## Restrições do projeto

- Python 3.14, FastAPI, Poetry; camadas verificadas por import-linter; CI com
  flake8/black/bandit/pytest; repositório no GitHub com ruleset (mudanças por PR).
- SQLite, uma réplica, um worker uvicorn. Frontend Vue 3 + Vite servido por nginx.
- `docker-compose.yml` hoje tem só `backend` e `frontend` (porta 8080).

## Abordagens consideradas

| Abordagem | Troca | Decisão |
|---|---|---|
| **A. SDK configurado à mão + `FastAPIInstrumentor`** | Mais código, cada peça visível e testável | **Escolhida pelo usuário** |
| B. Auto-instrumentação (`opentelemetry-instrument`) | Rápida, esconde o SDK | Aula de comparação |
| C. `prometheus_client` + coleta de logs do Docker | Cada sinal por um caminho; foge do OTel | Descartada |
| Imagem `grafana/otel-lgtm` | Esconde a config que é o objeto de estudo e o hardening | Descartada |

Onde rodar: **Compose primeiro, kind depois** (escolha do usuário).

## Design

### Fluxo

```
navegador (OTel web) ─traceparent─► nginx ─► backend (SDK OTel)
       │                                         │
       └────────OTLP/HTTP (via proxy)────────────┴──OTLP──► otel-collector
                                                    ├─ redação, memory_limiter, batch, tail sampling
                                                    ├──► Tempo        (traces)
                                                    ├──► /metrics ◄── Prometheus ──► Alertmanager
                                                    └──► Loki         (logs)
                                   Grafana ◄── Tempo, Prometheus, Loki
```

O navegador não fala direto com o Collector: o nginx encaminha só o caminho OTLP de traces,
com limite de tamanho. *Minha escolha, para não expor o Collector.*

### Backend
- `backend/telemetry.py` ao lado da composition root: `Resource` (`service.name`,
  `service.version`, `deployment.environment`), três providers, exporters OTLP, sampler.
  Sem `OTEL_EXPORTER_OTLP_ENDPOINT`: no-op.
- Spans HTTP via `FastAPIInstrumentor`; span manual no `SqliteRepository` (sem o SQL com
  valores, só operação/tabela). *Minha escolha: manual, para aprender a API.*
- Contador de negócio `todo.tasks.created` no adaptador `api/`. *Minha escolha (camadas).*
- `logging` + `LoggingHandler` do SDK; logs estruturados também no stdout.
- Testes com `InMemorySpanExporter`, `InMemoryMetricReader` e exporter de logs em memória;
  teste de "nenhum dado sensível em nenhum sinal".

### Infra
- Configs em `infra/observability/`. *Minha escolha.*
- Prometheus raspa o exporter `prometheus` do Collector (modelo pull). *Minha escolha.*
- Alertmanager com destino local (webhook de teste), sem integração externa.

### Módulos (cada um termina funcionando, testado e com gates verdes)

0. **Fundamentos e ameaças:** sinais, API × SDK, Collector; modelo de ameaças STRIDE inicial;
   ADR da arquitetura; gitleaks no pre-commit e no CI.
1. **Traces no backend:** `TracerProvider`, `FastAPIInstrumentor`, Collector com `debug`;
   teste em memória; teste de dado sensível (barreira 1). Por dentro: `contextvars`,
   `SpanProcessor` próprio, flush no `shutdown`; comparação com a auto-instrumentação.
2. **Tempo + Grafana com hardening:** redes separadas, só Grafana em `127.0.0.1`, segredos,
   containers endurecidos, digests; Trivy config/imagem no CI.
3. **Span do SQLite e propagação no frontend:** span manual; OTel web no Vue; trace de ponta
   a ponta passando pelo nginx.
4. **Métricas a fundo:** instrumentos, temporalidade, histogramas, Views/cardinalidade,
   runtime, Prometheus, PromQL.
5. **Exemplars e correlação:** métrica → trace, log → trace, trace → logs.
6. **Logs:** estruturados, CWE-117, Loki com limites e retenção.
7. **Pipeline resiliente e redação:** `memory_limiter`, `batch`, retry/fila, processor de
   redação (barreira 2) com teste, OTTL, telemetria do Collector; Collector próprio com ocb.
8. **Amostragem:** head × tail, efeitos nos dados e nos custos.
9. **SLO e alertas:** SLIs, error budget, burn rate multijanela, `promtool test rules`,
   Alertmanager, runbooks.
10. **Detecção como código:** regras para padrões suspeitos, testes, runbooks.
11. **Custo da instrumentação:** `make load` com/sem OTel e por amostragem.
12. **Game day:** derrubar Loki/Collector, inundar requisições, quebrar config; postmortem.
13. **Cadeia de suprimentos e CI completo:** SBOM, Dependabot de digests, assinaturas,
    todos os gates revisados.
14. **Fase 2, kind:** mTLS, auth nos receivers, NetworkPolicy, Pod Security `restricted`.

### Critério de sucesso

1. `make up` + `make load`: no Grafana, do painel SLO até uma requisição lenta, ao trace de
   ponta a ponta (navegador → SQLite) e aos logs dela.
2. Um game day dispara o alerta certo, o runbook resolve, e o postmortem existe.
3. O CI barra: título de tarefa em telemetria, segredo commitado, vulnerabilidade
   alta/crítica, config insegura, regra de alerta quebrada.
4. O usuário explica o caminho de cada sinal e cada ameaça mitigada.

## Deixado para quem implementar

Versões exatas e digests, nomes finais de arquivos, alvos do Makefile, limiares iniciais
de SLO (a calibrar com `make load`).
