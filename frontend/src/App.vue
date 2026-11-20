<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import type { StatusFilter, TaskApi } from './api/types'
import { useTasks } from './composables/useTasks'
import EmptyState from './components/EmptyState.vue'
import Icon from './components/Icon.vue'
import TaskFilter from './components/TaskFilter.vue'
import TaskForm from './components/TaskForm.vue'
import TaskItem from './components/TaskItem.vue'

const UNDO_TIMEOUT_MS = 6000
const FILTERS: StatusFilter[] = ['pending', 'completed']

const props = defineProps<{ api: TaskApi; pageSize?: number }>()

// O filtro fica na URL (?status=pending): sobrevive a recarregar a página e pode ser compartilhado.
function filterFromUrl(): StatusFilter | undefined {
  const value = new URLSearchParams(location.search).get('status')
  return FILTERS.find((f) => f === value)
}

const {
  tasks,
  total,
  counts,
  hasMore,
  filter,
  error,
  loading,
  loadingMore,
  removed,
  load,
  loadMore,
  setFilter,
  create,
  edit,
  complete,
  reopen,
  remove,
  undoRemove,
  forgetRemoved,
  dismissError,
} = useTasks(props.api, { pageSize: props.pageSize, initialFilter: filterFromUrl() })

onMounted(load)

watch(filter, (value) => {
  const url = new URL(location.href)
  if (value) url.searchParams.set('status', value)
  else url.searchParams.delete('status')
  history.replaceState(history.state, '', url)
})

const today = (() => {
  const text = new Intl.DateTimeFormat('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())
  return text.charAt(0).toUpperCase() + text.slice(1)
})()

const percentDone = computed(() =>
  counts.value.all ? Math.round((counts.value.completed / counts.value.all) * 100) : 0,
)

const empty = computed(() => {
  if (filter.value === 'pending' && counts.value.completed > 0)
    return { kind: 'done', title: 'Tudo em dia!', hint: 'Nenhuma tarefa pendente. Bom trabalho.' } as const
  if (filter.value === 'pending') return { kind: 'none', title: 'Nenhuma tarefa pendente.' } as const
  if (filter.value === 'completed')
    return { kind: 'none', title: 'Nenhuma tarefa concluída.', hint: 'Conclua uma tarefa para vê-la aqui.' } as const
  return { kind: 'inbox', title: 'Nenhuma tarefa.', hint: 'Adicione a primeira no campo acima.' } as const
})

// O aviso "Desfazer" some sozinho depois de alguns segundos.
let undoTimer: ReturnType<typeof setTimeout> | undefined
watch(removed, (task) => {
  clearTimeout(undoTimer)
  if (task) undoTimer = setTimeout(forgetRemoved, UNDO_TIMEOUT_MS)
})
onUnmounted(() => clearTimeout(undoTimer))
</script>

<template>
  <main class="app">
    <header class="header">
      <div class="brand">
        <span class="logo" aria-hidden="true"><Icon name="check" /></span>
        <div>
          <h1>Tarefas</h1>
          <p class="today">{{ today }}</p>
        </div>
      </div>
      <div v-if="!loading && counts.all" class="progress">
        <span class="progress-label" data-test="progress">{{ counts.completed }} de {{ counts.all }} concluídas</span>
        <div
          class="progress-track"
          role="progressbar"
          aria-label="Progresso"
          aria-valuemin="0"
          aria-valuemax="100"
          :aria-valuenow="percentDone"
        >
          <div class="progress-fill" :style="{ width: `${percentDone}%` }" />
        </div>
      </div>
    </header>

    <section class="card new-task" data-test="new-task" aria-label="Nova tarefa">
      <TaskForm :submit="create" submit-label="Adicionar" />
    </section>

    <div v-if="error" role="alert" class="error">
      <span>{{ error }}</span>
      <button class="icon-button" data-test="dismiss-error" aria-label="Fechar aviso" @click="dismissError">
        <Icon name="close" />
      </button>
    </div>

    <TaskFilter :model-value="filter" :counts="loading ? undefined : counts" @update:model-value="setFilter" />

    <ul v-if="loading" class="tasks" data-test="loading" aria-busy="true" aria-label="Carregando tarefas">
      <li v-for="n in 3" :key="n" class="task skeleton" />
    </ul>
    <template v-else-if="tasks.length">
      <TransitionGroup tag="ul" name="task" class="tasks">
        <TaskItem
          v-for="task in tasks"
          :key="task.id"
          :task="task"
          :save="edit"
          @complete="complete"
          @reopen="reopen"
          @remove="remove"
        />
      </TransitionGroup>
      <button
        v-if="hasMore"
        class="load-more"
        data-test="load-more"
        :disabled="loadingMore"
        :aria-busy="loadingMore"
        @click="loadMore"
      >
        {{ loadingMore ? 'Carregando…' : `Carregar mais (${total - tasks.length} restantes)` }}
      </button>
    </template>
    <EmptyState v-else :kind="empty.kind" :title="empty.title" :hint="empty.hint" />

    <Transition name="toast">
      <div v-if="removed" class="toast" data-test="toast" role="status">
        <span>
          Tarefa <strong>{{ removed.title }}</strong> removida.
        </span>
        <button class="link" data-test="undo" @click="undoRemove">Desfazer</button>
        <button class="icon-button" aria-label="Fechar" @click="forgetRemoved"><Icon name="close" /></button>
      </div>
    </Transition>
  </main>
</template>
