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

/** Porta para o backend — os componentes dependem disto, não do fetch (DIP). */
export interface TaskApi {
  list(status?: StatusFilter): Promise<Task[]>
  create(input: TaskInput): Promise<Task>
  edit(id: string, input: TaskInput): Promise<Task>
  complete(id: string): Promise<Task>
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
