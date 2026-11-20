<script setup lang="ts">
import { onMounted, ref, useId, watch } from 'vue'
import type { TaskInput } from '../api/types'

const props = withDefaults(
  defineProps<{
    submit: (input: TaskInput) => Promise<boolean>
    submitLabel: string
    initial?: TaskInput
    cancellable?: boolean
    autofocus?: boolean
  }>(),
  { initial: () => ({ title: '', description: '' }), cancellable: false, autofocus: false },
)
const emit = defineEmits<{ cancel: [] }>()
const titleErrorId = `title-error-${useId()}`

const title = ref(props.initial.title)
const description = ref(props.initial.description)
const titleInput = ref<HTMLInputElement>()

const submitting = ref(false)
const titleError = ref<string | null>(null)

// O aviso some assim que o usuário começa a corrigir.
watch(title, () => {
  titleError.value = null
})

onMounted(() => {
  if (props.autofocus) titleInput.value?.focus()
})

async function onSubmit() {
  if (!title.value.trim()) {
    titleError.value = 'Dê um título para a tarefa.'
    titleInput.value?.focus()
    return
  }
  const sent = { title: title.value, description: description.value }
  submitting.value = true
  try {
    if (await props.submit(sent)) {
      // Só limpa o que não mudou: o usuário pode ter digitado enquanto esperava a resposta.
      if (title.value === sent.title) title.value = props.initial.title
      if (description.value === sent.description) description.value = props.initial.description
      titleInput.value?.focus()
    }
  } finally {
    submitting.value = false
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && props.cancellable) emit('cancel')
}
</script>

<template>
  <form class="task-form" @submit.prevent="onSubmit" @keydown="onKeydown">
    <div class="fields">
      <input
        ref="titleInput"
        v-model="title"
        class="title-input"
        data-test="title"
        placeholder="O que precisa ser feito?"
        aria-label="Título"
        autocomplete="off"
        :aria-invalid="titleError ? 'true' : undefined"
        :aria-describedby="titleError ? titleErrorId : undefined"
      />
      <p v-if="titleError" :id="titleErrorId" class="field-error" data-test="title-error">{{ titleError }}</p>
      <input
        v-model="description"
        class="description-input"
        data-test="description"
        placeholder="Detalhes (opcional)"
        aria-label="Descrição"
        autocomplete="off"
      />
    </div>
    <div class="form-actions">
      <button v-if="cancellable" type="button" class="ghost" data-test="cancel" @click="emit('cancel')">Cancelar</button>
      <button type="submit" class="primary" :disabled="submitting" :aria-busy="submitting">{{ submitLabel }}</button>
    </div>
  </form>
</template>
