<script setup lang="ts">
import Message from 'primevue/message'
import type { Nullable } from '@/app/types/nullable'

defineProps<{
  label: string
  inputId: string
  error: Nullable<string>
  hint?: string
}>()
</script>

<template>
  <div class="flex min-w-0 flex-col gap-2">
    <label
      :for="inputId"
      class="text-sm font-semibold text-fino-text"
    >
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
