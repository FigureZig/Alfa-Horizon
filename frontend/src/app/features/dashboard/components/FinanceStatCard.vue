<script setup lang="ts">
defineProps<{
  title: string
  value: string
  icon: string
  description: string
}>()
</script>

<template>
  <article
    class="group flex min-w-0 flex-col gap-6
           rounded-3xl border border-fino-border bg-fino-surface
           p-5 shadow-sm transition-all duration-300
           hover:-translate-y-1 hover:shadow-md sm:p-6
           motion-reduce:transition-none motion-reduce:hover:translate-y-0"
  >
    <div class="flex items-start justify-between gap-3">
      <p class="text-sm font-medium text-fino-text-muted">
        {{ title }}
      </p>

      <div
        class="flex size-11 shrink-0 items-center justify-center
               rounded-2xl bg-fino-accent text-primary
               transition-transform group-hover:scale-110"
      >
        <i
          :class="icon"
          class="text-lg"
          aria-hidden="true"
        />
      </div>
    </div>

    <div class="min-w-0">
      <p class="break-words text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
        {{ value }}
      </p>

      <p class="mt-2 break-words text-sm text-fino-text-muted">
        {{ description }}
      </p>
    </div>
  </article>
</template>