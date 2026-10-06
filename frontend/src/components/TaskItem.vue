<script setup lang="ts">
import { ref } from 'vue'
import type { Task, TaskInput } from '../api/types'
import TaskForm from './TaskForm.vue'

const props = defineProps<{
  task: Task
  save: (id: string, input: TaskInput) => Promise<boolean>
}>()
const emit = defineEmits<{ complete: [id: string]; remove: [id: string] }>()

const editing = ref(false)

async function onSave(input: TaskInput) {
  const ok = await props.save(props.task.id, input)
  if (ok) editing.value = false
  return ok
}
</script>

<template>
  <li class="task" :class="{ done: task.status === 'COMPLETED' }" data-test="task">
    <TaskForm
      v-if="editing"
      :submit="onSave"
      :initial="{ title: task.title, description: task.description }"
      submit-label="Salvar"
      cancellable
      @cancel="editing = false"
    />
    <template v-else>
      <div class="text">
        <strong>{{ task.title }}</strong>
        <span v-if="task.description" class="description">{{ task.description }}</span>
      </div>
      <div class="actions">
        <button v-if="task.status === 'PENDING'" data-test="complete" @click="emit('complete', task.id)">Concluir</button>
        <button data-test="edit" @click="editing = true">Editar</button>
        <button data-test="remove" @click="emit('remove', task.id)">Remover</button>
      </div>
    </template>
  </li>
</template>
