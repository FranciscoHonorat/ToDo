<script setup lang="ts">
/** Estado vazio ilustrado: "inbox" (nada criado ainda), "done" (nada pendente) ou "none" (filtro sem resultado). */
defineProps<{ kind: 'inbox' | 'done' | 'none'; title: string; hint?: string }>()
</script>

<template>
  <div class="empty-state" :class="`empty-${kind}`">
    <svg class="illustration" viewBox="0 0 120 96" aria-hidden="true">
      <template v-if="kind === 'done'">
        <circle cx="60" cy="48" r="30" class="ill-soft" />
        <path d="M46 49l10 10 19-21" class="ill-stroke ill-accent" />
        <path d="M22 26l4 4M98 26l-4 4M20 66h6M94 66h6M60 6v6" class="ill-stroke ill-muted" />
      </template>
      <template v-else-if="kind === 'inbox'">
        <rect x="26" y="20" width="68" height="60" rx="10" class="ill-soft" />
        <path d="M40 40h40M40 52h28M40 64h18" class="ill-stroke ill-muted" />
        <circle cx="88" cy="22" r="11" class="ill-accent-fill" />
        <path d="M88 17v10M83 22h10" class="ill-stroke ill-on-accent" />
      </template>
      <template v-else>
        <circle cx="54" cy="44" r="20" class="ill-soft" />
        <circle cx="54" cy="44" r="20" class="ill-stroke ill-muted" fill="none" />
        <path d="M69 59l16 16" class="ill-stroke ill-muted" />
      </template>
    </svg>
    <p data-test="empty" class="empty">{{ title }}</p>
    <p v-if="hint" class="hint">{{ hint }}</p>
  </div>
</template>
