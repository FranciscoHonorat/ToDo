# SDKs da ToDo API

Três SDKs geradas a partir de [`docs/openapi.yaml`](../docs/openapi.yaml). Cada uma tem duas partes:

| Parte | O que é | Pode editar? |
|-------|---------|--------------|
| **Gerada** | tipos, modelos e uma função por rota | **Não** — rode `make sdks` |
| **Camada fina** | cliente com retry no 429 + iteração por todas as páginas | Sim |

| Linguagem | Gerador | Código gerado | Camada fina |
|-----------|---------|---------------|-------------|
| TypeScript | [openapi-typescript](https://openapi-ts.dev) + [openapi-fetch](https://openapi-ts.dev/openapi-fetch/) | `typescript/src/schema.ts` | `typescript/src/index.ts` |
| Python | [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) | `python/todo_api_client/generated/` | `python/todo_api_client/__init__.py` |
| Go | [oapi-codegen](https://github.com/oapi-codegen/oapi-codegen) (fixado como `tool` no `go.mod`) | `go/todo/client.gen.go` | `go/todo/sdk.go` |

## Fluxo quando a API muda

1. Mude o backend (com testes).
2. `make sdks` — regenera `docs/openapi.yaml` e o código gerado das três SDKs.
3. `make test-sdks` — testes unitários + cada SDK contra a API real (sobe o uvicorn do `backend/.venv`).
4. Versione o spec **e** o código gerado juntos. `make sdks-check` falha se esquecer.

## Rate limit nas SDKs

As três repetem automaticamente requisições que recebem `429`, esperando o `Retry-After`:
até **3 retries** e no máximo **60 s** de espera por vez (acima disso devolvem o próprio 429).
Ajuste: `maxRetries`/`maxDelaySeconds` (TS), `max_retries`/`max_delay_seconds` (Python),
`WithMaxRetries`/`WithMaxDelay` (Go).

## TypeScript

```ts
import { createTodoClient, iterateTasks } from 'todo-api-client'

const client = createTodoClient({ baseUrl: 'http://localhost:8080/api' })

const { data: task, error } = await client.POST('/tasks', { body: { title: 'Comprar pão', description: '' } })
if (error) throw new Error(JSON.stringify(error))

await client.POST('/tasks/{task_id}/complete', { params: { path: { task_id: task!.id } } })

for await (const t of iterateTasks(client, { status: 'pending' })) console.log(t.title)
```

Rotas, parâmetros e respostas são checados pelo compilador: um path errado ou um campo a menos não compila.

## Python

```python
from todo_api_client import create_client, iter_tasks
from todo_api_client.generated.api.tasks import complete_task, create_task
from todo_api_client.generated.models import TaskInput

client = create_client("http://localhost:8080/api")

task = create_task.sync(client=client, body=TaskInput(title="Comprar pão"))
complete_task.sync(client=client, task_id=task.id)

for t in iter_tasks(client, status="pending"):
    print(t.title)
```

Cada rota tem `sync`, `sync_detailed` (com status e headers), `asyncio` e `asyncio_detailed`.
Requer Python ≥ 3.11 (exigência do gerador) e usa `httpx2`.

## Go

```go
client, err := todo.New("http://localhost:8080/api")

created, err := client.CreateTaskWithResponse(ctx, todo.TaskInput{Title: "Comprar pão"})
if created.JSON201 == nil { /* created.JSON422, created.JSON429, created.Body ... */ }

_, err = client.CompleteTaskWithResponse(ctx, created.JSON201.Id)

for task, err := range todo.AllTasks(ctx, client, nil, 100) { // iter.Seq2 (Go 1.23+)
    if err != nil { return err }
    fmt.Println(task.Title)
}
```

`todo.New` devolve o `*ClientWithResponses` gerado; cada status documentado vira um campo tipado
(`JSON200`, `JSON404`, `JSON429`...). Os headers documentados também têm tipos (`ListTasksResponse200Headers`).
