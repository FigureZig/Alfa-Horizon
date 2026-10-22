<script setup lang="ts">
defineProps<{
  label: string
  value: string
  hint?: string
  icon: string
  isAlert?: boolean
}>()
</script>

<template>
  <article class="flex min-w-0 flex-col gap-3 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm">
    <div class="flex items-start justify-between gap-3">
      <p class="text-sm font-medium text-fino-text-muted">
        {{ label }}
      </p>

      <span
        class="flex size-10 shrink-0 items-center justify-center rounded-2xl"
        :class="isAlert ? 'bg-red-500/10 text-red-700 dark:text-red-400' : 'bg-fino-accent text-primary'"
        aria-hidden="true"
      >
        <i
          :class="icon"
          class="text-base"
        />
      </span>
    </div>

    <div class="min-w-0">
      <p class="break-words text-3xl font-bold tracking-tight text-fino-text">
        {{ value }}
      </p>

      <p
        v-if="hint"
        class="mt-1 text-xs text-fino-text-muted"
      >
        {{ hint }}
      </p>
    </div>
  </article>
</template>
