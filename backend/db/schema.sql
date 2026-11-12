CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Listagem filtrada por status na ordem de criação (o rowid entra no índice
-- implicitamente, então ORDER BY created_at, rowid sai pronto, sem ordenar).
CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks (status, created_at);
