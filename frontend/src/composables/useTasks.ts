import { computed, ref } from 'vue'
import type { StatusFilter, Task, TaskApi, TaskInput } from '../api/types'
import { errorMessage, isNotFound } from './errorMessage'

export interface UseTasksOptions {
  /** Quantas tarefas buscar por vez ("Carregar mais" traz a próxima página). */
  pageSize?: number
  initialFilter?: StatusFilter
}

export const DEFAULT_PAGE_SIZE = 20

export function useTasks(api: TaskApi, { pageSize = DEFAULT_PAGE_SIZE, initialFilter }: UseTasksOptions = {}) {
  const tasks = ref<Task[]>([])
  const total = ref(0)
  const filter = ref<StatusFilter | undefined>(initialFilter)
  const error = ref<string | null>(null)
  /** Começa true: até o primeiro load terminar, não sabemos se a lista está vazia. */
  const loading = ref(true)
  const loadingMore = ref(false)
  /** Última tarefa removida — permite "Desfazer". */
  const removed = ref<Task | null>(null)
  /** Quantas tarefas o usuário já pediu para ver; recarregar mantém as páginas abertas. */
  const shown = ref(pageSize)

  /** Totais por status, independentes do filtro (alimentam o progresso e os contadores dos filtros). */
  const counts = ref({ all: 0, pending: 0, completed: 0 })

  const hasMore = computed(() => tasks.value.length < total.value)

  /** Só o X-Total-Count interessa: limit=1 deixa a consulta barata. */
  const countOf = async (status: StatusFilter) => (await api.list({ status, limit: 1 })).total

  async function load() {
    const [page, pending, completed] = await Promise.all([
      api.list({ status: filter.value, limit: shown.value }),
      countOf('pending'),
      countOf('completed'),
    ])
    tasks.value = page.items
    total.value = page.total
    counts.value = { all: pending + completed, pending, completed }
  }

  /** Executa uma ação, recarrega a lista e centraliza o tratamento de erro (DRY). */
  async function run(action: () => Promise<unknown>): Promise<boolean> {
    try {
      await action()
      await load()
      error.value = null
      return true
    } catch (e) {
      error.value = errorMessage(e)
      // A tarefa sumiu (ex.: removida em outra aba): mostra a lista como ela está agora.
      if (isNotFound(e)) await load().catch(() => {})
      return false
    }
  }

  async function initialLoad() {
    loading.value = true
    try {
      return await run(async () => {})
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    loadingMore.value = true
    try {
      return await run(async () => {
        shown.value = tasks.value.length + pageSize
      })
    } finally {
      loadingMore.value = false
    }
  }

  function setFilter(value?: StatusFilter) {
    return run(async () => {
      filter.value = value
      shown.value = pageSize
    })
  }

  function remove(id: string) {
    const task = tasks.value.find((t) => t.id === id) ?? null
    return run(async () => {
      await api.remove(id)
      removed.value = task
    })
  }

  /** O backend não tem "lixeira": desfazer recria a tarefa (novo id) com o mesmo conteúdo e status. */
  function undoRemove() {
    const task = removed.value
    if (!task) return Promise.resolve(false)
    removed.value = null
    return run(async () => {
      const created = await api.create({ title: task.title, description: task.description })
      if (task.status === 'COMPLETED') await api.complete(created.id)
    })
  }

  return {
    tasks,
    total,
    counts,
    hasMore,
    filter,
    error,
    loading,
    loadingMore,
    removed,
    load: initialLoad,
    loadMore,
    setFilter,
    create: (input: TaskInput) => run(() => api.create(input)),
    edit: (id: string, input: TaskInput) => run(() => api.edit(id, input)),
    complete: (id: string) => run(() => api.complete(id)),
    reopen: (id: string) => run(() => api.reopen(id)),
    remove,
    undoRemove,
    forgetRemoved: () => {
      removed.value = null
    },
    dismissError: () => {
      error.value = null
    },
  }
}
