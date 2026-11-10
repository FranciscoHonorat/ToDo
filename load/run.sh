#!/usr/bin/env bash
# Teste de carga da API com Vegeta (taxa constante) e/ou Locust (usuários).
#
# Uso:  load/run.sh [vegeta|locust|all]
#
# Variáveis (com padrão):
#   TARGET=              URL da API. Vazio = cada cenário (vegeta-read, vegeta-write, locust)
#                        sobe seu próprio uvicorn com um banco temporário novo, para que os dados
#                        gravados por um cenário não deixem o seguinte mais lento.
#                        Ex.: TARGET=http://localhost:8080/api (compose). CUIDADO: grava dados lá,
#                        e os cenários compartilham o mesmo banco (os resultados se contaminam).
#   RATE=100             Vegeta: requisições por segundo.
#   DURATION=15s         Duração de cada ataque/execução.
#   USERS=50             Locust: usuários simultâneos.
#   SPAWN=10             Locust: usuários iniciados por segundo.
#   SEED=200             Tarefas criadas antes do Vegeta (para GET /tasks/{id}).
set -euo pipefail

MODE="${1:-all}"
RATE="${RATE:-100}"
DURATION="${DURATION:-15s}"
USERS="${USERS:-50}"
SPAWN="${SPAWN:-10}"
SEED="${SEED:-200}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/backend/.venv/bin/python"
VEGETA="$(command -v vegeta || echo "$HOME/go/bin/vegeta")"
OUT="$ROOT/load/results/$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d)"
SERVER_PID=""
EXTERNAL_TARGET="${TARGET:-}"
mkdir -p "$OUT"

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

# Sobe um uvicorn com banco vazio em $WORK/<nome>.db e aponta TARGET para ele.
start_server() {
  local name="$1" port db
  db="$WORK/$name.db"
  port="$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
  TARGET="http://127.0.0.1:$port"
  echo "→ [$name] subindo uvicorn em $TARGET (banco novo $db)"
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

# Executa um ataque do Vegeta e gera relatório texto, JSON, histograma e gráfico HTML.
attack() {
  local name="$1" targets="$2"
  echo
  echo "━━ Vegeta: $name — $RATE req/s por $DURATION ━━"
  "$VEGETA" attack -targets="$targets" -format=http -rate="$RATE" -duration="$DURATION" \
    > "$OUT/vegeta-$name.bin"
  "$VEGETA" report < "$OUT/vegeta-$name.bin" | tee "$OUT/vegeta-$name.txt"
  "$VEGETA" report -type=json < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name.json"
  "$VEGETA" report -type='hist[0,1ms,2ms,5ms,10ms,25ms,50ms,100ms,250ms,500ms]' \
    < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name-hist.txt"
  "$VEGETA" plot -title="$name" < "$OUT/vegeta-$name.bin" > "$OUT/vegeta-$name.html"
}

run_vegeta() {
  fresh_server vegeta-read
  echo "→ criando $SEED tarefas de base"
  : > "$WORK/ids"
  for _ in $(seq "$SEED"); do
    curl -sf -XPOST "$TARGET/tasks" -H 'Content-Type: application/json' \
      -d '{"title":"seed"}' | jq -r .id >> "$WORK/ids"
  done

  # Leitura: GET /tasks/{id} em rodízio pelas tarefas criadas.
  sed "s#^#GET $TARGET/tasks/#" "$WORK/ids" | sed 'a\\' > "$WORK/read.txt"

  attack read "$WORK/read.txt"

  # Escrita: POST /tasks com corpo JSON, num banco novo (não herda as tarefas de base).
  fresh_server vegeta-write
  echo '{"title":"vegeta","description":"carga"}' > "$WORK/body.json"
  printf 'POST %s/tasks\nContent-Type: application/json\n@%s\n\n' "$TARGET" "$WORK/body.json" \
    > "$WORK/write.txt"

  attack write "$WORK/write.txt"
}

run_locust() {
  fresh_server locust
  echo
  echo "━━ Locust: $USERS usuários (+$SPAWN/s) por $DURATION ━━"
  "$PY" -m locust -f "$ROOT/load/locustfile.py" --headless --host "$TARGET" \
    -u "$USERS" -r "$SPAWN" -t "$DURATION" --only-summary \
    --csv "$OUT/locust" --html "$OUT/locust.html" 2>&1 | grep -v RuntimeWarning
}

case "$MODE" in
  vegeta) run_vegeta ;;
  locust) run_locust ;;
  all)    run_vegeta; run_locust ;;
  *) echo "modo inválido: $MODE (use vegeta|locust|all)" >&2; exit 2 ;;
esac

echo
echo "Resultados em ${OUT#$ROOT/}/  (abra os .html no navegador)"
