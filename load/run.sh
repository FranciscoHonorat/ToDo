#!/usr/bin/env bash
# Teste de carga da API com Vegeta (taxa constante) e/ou Locust (usuários).
#
# Uso:  load/run.sh [vegeta|locust|all]
#
# Variáveis (com padrão):
#   TARGET=              URL da API. Vazio = sobe um uvicorn próprio com banco temporário.
#                        Ex.: TARGET=http://localhost:8080/api (compose). CUIDADO: grava dados lá.
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
PY="$ROOT/.venv/bin/python"
VEGETA="$(command -v vegeta || echo "$HOME/go/bin/vegeta")"
OUT="$ROOT/load/results/$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d)"
SERVER_PID=""
mkdir -p "$OUT"

cleanup() {
  [[ -n "$SERVER_PID" ]] && kill "$SERVER_PID" 2>/dev/null && wait "$SERVER_PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

start_server() {
  local port
  port="$("$PY" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
  TARGET="http://127.0.0.1:$port"
  echo "→ subindo uvicorn em $TARGET (banco temporário $WORK/load.db)"
  (cd "$ROOT/backend" && TODO_DATABASE="$WORK/load.db" exec "$PY" -m uvicorn server:app \
      --port "$port" --no-access-log --log-level warning) &
  SERVER_PID=$!
  for _ in $(seq 50); do curl -sf "$TARGET/health" >/dev/null && return; sleep 0.2; done
  echo "uvicorn não subiu" >&2; exit 1
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
  echo "→ criando $SEED tarefas de base"
  : > "$WORK/ids"
  for _ in $(seq "$SEED"); do
    curl -sf -XPOST "$TARGET/tasks" -H 'Content-Type: application/json' \
      -d '{"title":"seed"}' | jq -r .id >> "$WORK/ids"
  done

  # Leitura: GET /tasks/{id} em rodízio pelas tarefas criadas.
  sed "s#^#GET $TARGET/tasks/#" "$WORK/ids" | sed 'a\\' > "$WORK/read.txt"

  # Escrita: POST /tasks com corpo JSON.
  echo '{"title":"vegeta","description":"carga"}' > "$WORK/body.json"
  printf 'POST %s/tasks\nContent-Type: application/json\n@%s\n\n' "$TARGET" "$WORK/body.json" \
    > "$WORK/write.txt"

  attack read "$WORK/read.txt"
  attack write "$WORK/write.txt"
}

run_locust() {
  echo
  echo "━━ Locust: $USERS usuários (+$SPAWN/s) por $DURATION ━━"
  "$PY" -m locust -f "$ROOT/load/locustfile.py" --headless --host "$TARGET" \
    -u "$USERS" -r "$SPAWN" -t "$DURATION" --only-summary \
    --csv "$OUT/locust" --html "$OUT/locust.html" 2>&1 | grep -v RuntimeWarning
}

if [[ -z "${TARGET:-}" ]]; then start_server; else echo "→ usando TARGET=$TARGET"; fi

case "$MODE" in
  vegeta) run_vegeta ;;
  locust) run_locust ;;
  all)    run_vegeta; run_locust ;;
  *) echo "modo inválido: $MODE (use vegeta|locust|all)" >&2; exit 2 ;;
esac

echo
echo "Resultados em ${OUT#$ROOT/}/  (abra os .html no navegador)"
