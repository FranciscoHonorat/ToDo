<script setup lang="ts">
import { onMounted } from 'vue'
import type { TaskApi } from './api/types'
import { useTasks } from './composables/useTasks'
import TaskFilter from './components/TaskFilter.vue'
import TaskForm from './components/TaskForm.vue'
import TaskItem from './components/TaskItem.vue'

const props = defineProps<{ api: TaskApi }>()
const { tasks, filter, error, load, setFilter, create, edit, complete, remove } = useTasks(props.api)

onMounted(load)
</script>

<template>
  <main class="app">
    <h1>Tarefas</h1>
    <section data-test="new-task">
      <TaskForm :submit="create" submit-label="Adicionar" />
    </section>
    <p v-if="error" role="alert" class="error">{{ error }}</p>
    <TaskFilter :model-value="filter" @update:model-value="setFilter" />
    <ul v-if="tasks.length" class="tasks">
      <TaskItem v-for="task in tasks" :key="task.id" :task="task" :save="edit" @complete="complete" @remove="remove" />
    </ul>
    <p v-else data-test="empty" class="empty">Nenhuma tarefa.</p>
  </main>
</template>
