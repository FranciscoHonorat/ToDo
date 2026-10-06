import { ref } from 'vue'
import type { StatusFilter, Task, TaskApi, TaskInput } from '../api/types'

export function useTasks(api: TaskApi) {
  const tasks = ref<Task[]>([])
  const filter = ref<StatusFilter | undefined>()
  const error = ref<string | null>(null)

  async function load() {
    tasks.value = await api.list(filter.value)
  }

  /** Executa uma ação, recarrega a lista e centraliza o tratamento de erro (DRY). */
  async function run(action: () => Promise<unknown>): Promise<boolean> {
    try {
      await action()
      await load()
      error.value = null
      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return false
    }
  }

  return {
    tasks,
    filter,
    error,
    load: () => run(async () => {}),
    setFilter: (value?: StatusFilter) => run(async () => { filter.value = value }),
    create: (input: TaskInput) => run(() => api.create(input)),
    edit: (id: string, input: TaskInput) => run(() => api.edit(id, input)),
    complete: (id: string) => run(() => api.complete(id)),
    remove: (id: string) => run(() => api.remove(id)),
  }
}
