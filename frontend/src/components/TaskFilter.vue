<script setup lang="ts">
import type { StatusFilter } from '../api/types'

defineProps<{ modelValue: StatusFilter | undefined }>()
const emit = defineEmits<{ 'update:modelValue': [value: StatusFilter | undefined] }>()

const options: { name: string; label: string; value: StatusFilter | undefined }[] = [
  { name: 'all', label: 'Todas', value: undefined },
  { name: 'pending', label: 'Pendentes', value: 'pending' },
  { name: 'completed', label: 'Concluídas', value: 'completed' },
]
</script>

<template>
  <div class="filter" role="group" aria-label="Filtrar por status">
    <button
      v-for="option in options"
      :key="option.name"
      :data-test="`filter-${option.name}`"
      :aria-pressed="modelValue === option.value"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>
