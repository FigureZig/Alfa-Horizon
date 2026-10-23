<script setup lang="ts">
import Message from 'primevue/message'
import type { Nullable } from '@/app/types/nullable'

defineProps<{
  label: string
  inputId: string
  error: Nullable<string>
  hint?: string
  // Этот ответ называет причина в предпросмотре: слева рамка и метка
  isHighlighted?: boolean
}>()
</script>

<template>
  <div
    class="relative flex min-w-0 flex-col gap-2 rounded-2xl transition-all duration-200 motion-reduce:transition-none"
    :class="isHighlighted ? 'bg-fino-accent/60 ring-2 ring-primary/40 ring-offset-4 ring-offset-fino-surface' : ''"
  >
    <label
      :for="inputId"
      class="flex items-center gap-2 text-sm font-semibold text-fino-text"
    >
      <span
        v-if="isHighlighted"
        class="size-2 shrink-0 rounded-full bg-primary"
        aria-hidden="true"
      />
      {{ label }}
    </label>

    <slot />

    <p
      v-if="hint && !error"
      class="text-xs text-fino-text-muted"
    >
      {{ hint }}
    </p>

    <Message
      v-if="error"
      severity="error"
      size="small"
      variant="simple"
    >
      {{ error }}
    </Message>
  </div>
</template>
