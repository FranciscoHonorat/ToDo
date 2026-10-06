import os

from api.app import create_app
from composition import build_service, database_path, get_connection

# O FastAPI executa rotas síncronas num pool de threads; o SqliteRepository
# serializa o acesso à conexão com um lock (ver test_sqlite_concurrency.py).
connection = get_connection(database_path(), check_same_thread=False)

# Atrás do nginx a API fica sob /api; o root_path faz o Swagger UI (/docs)
# buscar o spec e enviar o "Try it out" pelo prefixo certo.
app = create_app(build_service(connection), root_path=os.environ.get("API_ROOT_PATH", ""))
