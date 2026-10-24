<script setup lang="ts">
defineProps<{
  icon: string
  title: string
  // Текущие ответы раздела одной строкой — видно и в свёрнутом виде
  summary: string
  isOpen?: boolean
}>()
</script>

<template>
  <details
    class="group rounded-2xl bg-fino-surface border-2 border-fino-line"
    :open="isOpen"
  >
    <summary
      class="flex cursor-pointer items-center gap-3 rounded-2xl px-4 py-3 marker:content-none
             focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span
        class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-surface-secondary text-fino-text-muted
               transition-colors duration-200 group-open:bg-fino-accent group-open:text-primary motion-reduce:transition-none border-2 border-fino-line"
        aria-hidden="true"
      >
        <i :class="icon" />
      </span>

      <span class="min-w-0 flex-1">
        <span class="block text-sm font-semibold text-fino-text">{{ title }}</span>
        <span
          v-if="summary"
          class="block truncate text-xs text-fino-text-muted"
        >{{ summary }}</span>
      </span>

      <i
        class="pi pi-chevron-down shrink-0 text-xs text-fino-text-muted transition-transform duration-200
               group-open:rotate-180 motion-reduce:transition-none"
        aria-hidden="true"
      />
    </summary>

    <slot />
  </details>
</template>
