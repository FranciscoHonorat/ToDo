import { ApiError, type ListQuery, type Task, type TaskApi, type TaskInput } from '../src/api/types'

/** Implementação em memória de TaskApi — o "MemoryRepository" do frontend. */
export class FakeTaskApi implements TaskApi {
  tasks: Task[] = []

  async list({ status, limit, offset = 0 }: ListQuery = {}) {
    const matching = this.tasks.filter((task) => !status || task.status === status.toUpperCase())
    const end = limit === undefined ? undefined : offset + limit
    return { items: matching.slice(offset, end).map((task) => ({ ...task })), total: matching.length }
  }

  async create(input: TaskInput) {
    this.validate(input)
    const task: Task = { id: crypto.randomUUID(), status: 'PENDING', ...input }
    this.tasks.push(task)
    return { ...task }
  }

  async edit(id: string, input: TaskInput) {
    this.validate(input)
    return { ...Object.assign(this.find(id), input) }
  }

  async complete(id: string) {
    return { ...Object.assign(this.find(id), { status: 'COMPLETED' as const }) }
  }

  async reopen(id: string) {
    return { ...Object.assign(this.find(id), { status: 'PENDING' as const }) }
  }

  async remove(id: string) {
    this.find(id)
    this.tasks = this.tasks.filter((task) => task.id !== id)
  }

  private find(id: string) {
    const task = this.tasks.find((task) => task.id === id)
    if (!task) throw new ApiError(`Task with ID ${id} not found.`, 404)
    return task
  }

  private validate(input: TaskInput) {
    if (!input.title.trim()) throw new ApiError('Title cannot be empty.', 422)
  }
}
