<script setup lang="ts">
import { ref } from 'vue'
import type { Task, TaskInput } from '../api/types'
import Icon from './Icon.vue'
import TaskForm from './TaskForm.vue'

const props = defineProps<{
  task: Task
  save: (id: string, input: TaskInput) => Promise<boolean>
}>()
const emit = defineEmits<{ complete: [id: string]; reopen: [id: string]; remove: [id: string] }>()

const editing = ref(false)

async function onSave(input: TaskInput) {
  const ok = await props.save(props.task.id, input)
  if (ok) editing.value = false
  return ok
}
</script>

<template>
  <li class="task" :class="{ done: task.status === 'COMPLETED', editing }" data-test="task">
    <TaskForm
      v-if="editing"
      :submit="onSave"
      :initial="{ title: task.title, description: task.description }"
      submit-label="Salvar"
      cancellable
      autofocus
      @cancel="editing = false"
    />
    <template v-else>
      <button
        v-if="task.status === 'PENDING'"
        class="check"
        data-test="complete"
        aria-label="Concluir"
        title="Concluir"
        @click="emit('complete', task.id)"
      >
        <Icon name="check" />
      </button>
      <button
        v-else
        class="check checked"
        data-test="reopen"
        aria-label="Reabrir"
        title="Concluída — clique para reabrir"
        @click="emit('reopen', task.id)"
      >
        <Icon name="check" />
      </button>

      <div class="text">
        <strong>{{ task.title }}</strong>
        <span v-if="task.description" class="description">{{ task.description }}</span>
      </div>

      <div class="actions">
        <button class="icon-button" data-test="edit" aria-label="Editar" title="Editar" @click="editing = true">
          <Icon name="edit" />
        </button>
        <button
          class="icon-button danger"
          data-test="remove"
          aria-label="Remover"
          title="Remover"
          @click="emit('remove', task.id)"
        >
          <Icon name="trash" />
        </button>
      </div>
    </template>
  </li>
</template>
