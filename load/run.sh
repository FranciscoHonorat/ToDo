#!/usr/bin/env bash
# Teste de carga da API com Vegeta (taxa constante) e/ou Locust (usuários),
# repetido para cada volume de dados declarado em VOLUMES.
#
# Uso:  load/run.sh [vegeta|locust|all]
#
# Variáveis (com padrão):
#   VOLUMES="1000"       Tamanhos de banco a testar, ex.: VOLUMES="0 1000 10000 100000".
#                        Cada cenário de cada volume começa num servidor e banco novos,
#                        populados com exatamente esse número de tarefas (load/seed.py).
#   PENDING_PCT=50       Porcentagem das tarefas de base que ficam pendentes.
#   LIST_LIMIT=50        Tamanho da página nas listagens (Vegeta "list" e Locust).
#                        0 = sem paginação, como o frontend lista hoje.
#   TARGET=              URL da API. Vazio = servidor próprio por cenário (recomendado).
#                        Ex.: TARGET=http://localhost:8080/api (compose). CUIDADO: grava dados lá,
#                        os cenários compartilham o banco, e o volume só é semeado via API
#                        (tarefas pendentes, uma requisição por tarefa, só no cenário read).
#   RATE=100             Vegeta: requisições por segundo.
#   DURATION=15s         Duração de cada ataque/execução.
#   USERS=50             Locust: usuários simultâneos.
#   SPAWN=10             Locust: usuários iniciados por segundo.
#
# Cada cenário registra total e pendentes no início e no fim (counts.csv), porque
# os cenários que escrevem fazem o banco crescer durante a própria rodada. No fim,
# summary.md junta latências e contagens por volume.
set -euo pipefail

MODE="${1:-all}"
VOLUMES="${VOLUMES:-1000}"
PENDING_PCT="${PENDING_PCT:-50}"
LIST_LIMIT="${LIST_LIMIT:-50}"
RATE="${RATE:-100}"
DURATION="${DURATION:-15s}"
USERS="${USERS:-50}"
SPAWN="${SPAWN:-10}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
VEGETA="$(command -v vegeta || echo "$HOME/go/bin/vegeta")"
RUN="$ROOT/load/results/$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d)"
SERVER_PID=""
EXTERNAL_TARGET="${TARGET:-}"
VOLUME=""
OUT=""
mkdir -p "$RUN"
echo "volume,scenario,phase,total,pending" > "$RUN/counts.csv"

case "$MODE" in vegeta | locust | all) ;; *)
  echo "modo inválido: $MODE (use vegeta|locust|all)" >&2; exit 2 ;;
esac

stop_server() {
  if [[ -n "$SERVER_PID" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    SERVER_PID=""
  fi
}

cleanup() {
  stop_server
  rm -rf "$WORK"
}
trap cleanup EXIT

# Sobe um uvicorn com um banco novo em $WORK/<nome>.db, já populado com $VOLUME tarefas.
start_server() {
  local name="$1" port db
  db="$WORK/$VOLUME-$name.db"
  "$PY" "$ROOT/load/seed.py" "$db" --total "$VOLUME" --pending-pct "$PENDING_PCT" --ids "$WORK/ids"
  port="$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
  TARGET="http://127.0.0.1:$port"
  echo "→ [$name] uvicorn em $TARGET, banco novo com $VOLUME tarefas ($PENDING_PCT% pendentes)"
  (cd "$ROOT/backend" && TODO_DATABASE="$db" exec "$PY" -m uvicorn server:app \
      --port "$port" --no-access-log --log-level warning) &
  SERVER_PID=$!
  for _ in $(seq 50); do curl -sf "$TARGET/health" >/dev/null && return; sleep 0.2; done
  echo "uvicorn não subiu" >&2; exit 1
}

# Cada cenário começa num servidor e banco novos, a menos que TARGET seja externo.
fresh_server() {
  local name="$1"
  if [[ -n "$EXTERNAL_TARGET" ]]; then
    echo "→ [$name] usando TARGET=$TARGET (banco compartilhado entre cenários)"
    return
  fi
  stop_server
  start_server "$name"
}

# Quantas tarefas a API diz ter (cabeçalho X-Total-Count); $1 = status opcional.
count_tasks() {
  curl -s -D - -o /dev/null "$TARGET/tasks?limit=1${1:+&status=$1}" |
    tr -d '\r' | awk -F': ' 'tolower($1) == "x-total-count" { print $2 }'
}

record_counts() {
  local name="$1" phase="$2" total pending
  total="$(count_tasks)"
  pending="$(count_tasks pending)"
  echo "$VOLUME,$name,$phase,${total:-n/d},${pending:-n/d}" >> "$RUN/counts.csv"
  echo "→ [$name] $phase: ${total:-n/d} tarefas, ${pending:-n/d} pendentes"
}

list_query() {
  echo "status=pending$( ((LIST_LIMIT > 0)) && echo "&limit=$LIST_LIMIT")"
}

# Executa um ataque do Vegeta e gera relatório texto, JSON, histograma e gráfico HTML.
attack() {
  local name="$1" targets="$2"
  echo
  echo "━━ Vegeta: $name — $RATE req/s por $DURATION (volume $VOLUME) ━━"
  "$VEGETA" attack -targets="$targets" -format=http -rate="$RATE" -duration="$DURATION" \
    > "$OUT/vegeta-$name.bin"
  "$VEGETA" report < "$OUT/vegeta-$name.bin" | tee "$OUT/vegeta-$name.txt"
  "$VEGETA" report -type=json < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name.json"
  "$VEGETA" report -type='hist[0,1ms,2ms,5ms,10ms,25ms,50ms,100ms,250ms,500ms]' \
    < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name-hist.txt"
  "$VEGETA" plot -title="$name (volume $VOLUME)" < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name.html"
}

run_vegeta() {
  # Leitura e listagem compartilham servidor: nenhuma das duas escreve, então o volume não muda.
  fresh_server vegeta-read
  if [[ -n "$EXTERNAL_TARGET" ]]; then
    echo "→ criando $VOLUME tarefas de base via API"
    : > "$WORK/ids"
    for _ in $(seq "$VOLUME"); do
      curl -sf -XPOST "$TARGET/tasks" -H 'Content-Type: application/json' \
        -d '{"title":"seed"}' | jq -r .id >> "$WORK/ids"
    done
  fi
  record_counts vegeta-read início

  # Leitura: GET /tasks/{id} em rodízio pelas tarefas de base.
  if [[ -s "$WORK/ids" ]]; then
    sed "s#^#GET $TARGET/tasks/#" "$WORK/ids" | sed 'a\\' > "$WORK/read.txt"
    attack read "$WORK/read.txt"
  else
    echo "→ [vegeta-read] volume 0: sem tarefas para GET /tasks/{id}, pulando"
  fi

  # Listagem: a mesma página de pendentes repetidamente, num banco de tamanho fixo.
  printf 'GET %s/tasks?%s\n\n' "$TARGET" "$(list_query)" > "$WORK/list.txt"
  attack list "$WORK/list.txt"
  record_counts vegeta-read fim

  # Escrita: POST /tasks com corpo JSON, num banco novo com o mesmo volume de base.
  fresh_server vegeta-write
  record_counts vegeta-write início
  echo '{"title":"vegeta","description":"carga"}' > "$WORK/body.json"
  printf 'POST %s/tasks\nContent-Type: application/json\n@%s\n\n' "$TARGET" "$WORK/body.json" \
    > "$WORK/write.txt"
  attack write "$WORK/write.txt"
  record_counts vegeta-write fim
}

run_locust() {
  fresh_server locust
  record_counts locust início
  echo
  echo "━━ Locust: $USERS usuários (+$SPAWN/s) por $DURATION (volume $VOLUME) ━━"
  LIST_LIMIT="$LIST_LIMIT" "$PY" -m locust -f "$ROOT/load/locustfile.py" --headless --host "$TARGET" \
    -u "$USERS" -r "$SPAWN" -t "$DURATION" --only-summary \
    --csv "$OUT/locust" --html "$OUT/locust.html" 2>&1 | grep -v RuntimeWarning
  record_counts locust fim
}

for VOLUME in $VOLUMES; do
  OUT="$RUN/seed-$VOLUME"
  mkdir -p "$OUT"
  echo
  echo "════ Volume: $VOLUME tarefas ════"
  case "$MODE" in
    vegeta) run_vegeta ;;
    locust) run_locust ;;
    all)    run_vegeta; run_locust ;;
  esac
done
stop_server

echo
echo "════ Resumo (latência em ms; contagens no início e no fim de cada cenário) ════"
"$PY" "$ROOT/load/summarize.py" "$RUN"
echo
echo "Resultados em ${RUN#$ROOT/}/  (summary.md, e os .html de cada volume no navegador)"
