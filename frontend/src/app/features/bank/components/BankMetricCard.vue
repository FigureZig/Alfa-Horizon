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
  <article class="flex min-w-0 flex-col gap-3 card-key p-5">
    <div class="flex items-start justify-between gap-3">
      <p class="text-sm font-medium text-fino-text-muted">
        {{ label }}
      </p>

      <span
        class="flex size-10 shrink-0 items-center justify-center rounded-2xl"
        :class="isAlert ? 'border-2 border-fino-line bg-primary text-primary-contrast' : 'bg-fino-accent text-primary'"
        aria-hidden="true"
      >
        <i
          :class="icon"
          class="text-base"
        />
      </span>
    </div>

    <div class="min-w-0">
      <p class="break-words text-3xl font-display font-black text-fino-text">
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
