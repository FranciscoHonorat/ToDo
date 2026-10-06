<script setup lang="ts">
import { ref } from 'vue'
import type { TaskInput } from '../api/types'

const props = withDefaults(
  defineProps<{
    submit: (input: TaskInput) => Promise<boolean>
    submitLabel: string
    initial?: TaskInput
    cancellable?: boolean
  }>(),
  { initial: () => ({ title: '', description: '' }), cancellable: false },
)
const emit = defineEmits<{ cancel: [] }>()

const title = ref(props.initial.title)
const description = ref(props.initial.description)

const submitting = ref(false)

async function onSubmit() {
  const sent = { title: title.value, description: description.value }
  submitting.value = true
  try {
    if (await props.submit(sent)) {
      // Só limpa o que não mudou: o usuário pode ter digitado enquanto esperava a resposta.
      if (title.value === sent.title) title.value = props.initial.title
      if (description.value === sent.description) description.value = props.initial.description
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <form class="task-form" @submit.prevent="onSubmit">
    <input v-model="title" data-test="title" placeholder="Título" aria-label="Título" />
    <input v-model="description" data-test="description" placeholder="Descrição" aria-label="Descrição" />
    <button type="submit" :disabled="submitting">{{ submitLabel }}</button>
    <button v-if="cancellable" type="button" data-test="cancel" @click="emit('cancel')">Cancelar</button>
  </form>
</template>
