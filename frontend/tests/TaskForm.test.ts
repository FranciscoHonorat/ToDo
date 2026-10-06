import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TaskForm from '../src/components/TaskForm.vue'

function mountForm(props: Record<string, unknown> = {}) {
  const submit = vi.fn(async () => true)
  const wrapper = mount(TaskForm, { props: { submit, submitLabel: 'Adicionar', ...props } })
  return { wrapper, submit }
}

describe('TaskForm', () => {
  it('submits the typed title and description', async () => {
    const { wrapper, submit } = mountForm()

    await wrapper.get('[data-test="title"]').setValue('Comprar pão')
    await wrapper.get('[data-test="description"]').setValue('na padaria')
    await wrapper.get('form').trigger('submit')

    expect(submit).toHaveBeenCalledWith({ title: 'Comprar pão', description: 'na padaria' })
  })

  it('clears the fields when submit succeeds', async () => {
    const { wrapper } = mountForm()

    await wrapper.get('[data-test="title"]').setValue('Comprar pão')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect((wrapper.get('[data-test="title"]').element as HTMLInputElement).value).toBe('')
  })

  it('keeps the fields when submit fails', async () => {
    const { wrapper } = mountForm({ submit: vi.fn(async () => false) })

    await wrapper.get('[data-test="title"]').setValue('Comprar pão')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect((wrapper.get('[data-test="title"]').element as HTMLInputElement).value).toBe('Comprar pão')
  })

  it('starts with the initial values (used for editing)', () => {
    const { wrapper } = mountForm({ initial: { title: 'Velho', description: 'desc' } })

    expect((wrapper.get('[data-test="title"]').element as HTMLInputElement).value).toBe('Velho')
    expect((wrapper.get('[data-test="description"]').element as HTMLInputElement).value).toBe('desc')
  })

  it('shows the submit label', () => {
    const { wrapper } = mountForm({ submitLabel: 'Salvar' })

    expect(wrapper.get('button[type="submit"]').text()).toBe('Salvar')
  })

  it('only shows cancel when cancellable and emits cancel', async () => {
    expect(mountForm().wrapper.find('[data-test="cancel"]').exists()).toBe(false)

    const { wrapper } = mountForm({ cancellable: true })
    await wrapper.get('[data-test="cancel"]').trigger('click')

    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('does not wipe what was typed while the previous submit was in flight', async () => {
    let finish!: (ok: boolean) => void
    const submit = vi.fn(() => new Promise<boolean>((resolve) => (finish = resolve)))
    const { wrapper } = mountForm({ submit })
    const title = wrapper.get('[data-test="title"]')

    await title.setValue('Primeira')
    await wrapper.get('form').trigger('submit')
    await title.setValue('Segunda')
    finish(true)
    await flushPromises()

    expect((title.element as HTMLInputElement).value).toBe('Segunda')
  })

  it('disables the submit button while submitting to avoid double submits', async () => {
    let finish!: (ok: boolean) => void
    const { wrapper } = mountForm({ submit: vi.fn(() => new Promise<boolean>((resolve) => (finish = resolve))) })
    const button = wrapper.get('button[type="submit"]')

    await wrapper.get('form').trigger('submit')
    expect(button.attributes('disabled')).toBeDefined()

    finish(true)
    await flushPromises()
    expect(button.attributes('disabled')).toBeUndefined()
  })
})
