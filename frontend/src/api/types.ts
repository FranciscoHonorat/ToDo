export type TaskStatus = 'PENDING' | 'COMPLETED'

export type StatusFilter = 'pending' | 'completed'

export interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
}

export interface TaskInput {
  title: string
  description: string
}

export interface ListQuery {
  status?: StatusFilter
  limit?: number
  offset?: number
}

/** Uma página da listagem; `total` conta todas as tarefas do filtro (header X-Total-Count). */
export interface TaskPage {
  items: Task[]
  total: number
}

/** Porta para o backend — os componentes dependem disto, não do fetch (DIP). */
export interface TaskApi {
  list(query?: ListQuery): Promise<TaskPage>
  create(input: TaskInput): Promise<Task>
  edit(id: string, input: TaskInput): Promise<Task>
  complete(id: string): Promise<Task>
  reopen(id: string): Promise<Task>
  remove(id: string): Promise<void>
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}
