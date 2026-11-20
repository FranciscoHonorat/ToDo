import os

from api.app import create_app
from api.rate_limit import RateLimit
from composition import build_service, database_path, get_connection

# O FastAPI executa rotas síncronas num pool de threads; o SqliteRepository
# serializa o acesso à conexão com um lock (ver test_sqlite_concurrency.py).
connection = get_connection(database_path(), check_same_thread=False)

# Atrás do nginx a API fica sob /api; o root_path faz o Swagger UI (/docs)
# buscar o spec e enviar o "Try it out" pelo prefixo certo.
# Limite por cliente (IP): "300/minute" por padrão; "off" desliga (testes de carga, E2E).
DEFAULT_RATE_LIMIT = "300/minute"
rate_limit = RateLimit.parse(os.environ.get("TODO_RATE_LIMIT", DEFAULT_RATE_LIMIT))

app = create_app(build_service(connection), root_path=os.environ.get("API_ROOT_PATH", ""), rate_limit=rate_limit)
