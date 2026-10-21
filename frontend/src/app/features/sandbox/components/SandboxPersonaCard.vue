<script setup lang="ts">
import { computed } from 'vue'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

const props = defineProps<{
  persona: SandboxPersonaInterface
  isSelected: boolean
}>()

const emit = defineEmits<{
  select: [persona: SandboxPersonaInterface]
}>()

const cardStateClass = computed(() =>
  props.isSelected
    ? 'border-primary ring-1 ring-primary'
    : 'border-fino-border',
)

const avatarStateClass = computed(() =>
  props.isSelected
    ? 'bg-primary text-primary-contrast'
    : 'bg-fino-accent text-primary',
)

function handleSelect() {
  emit('select', props.persona)
}
</script>

<template>
  <button
    type="button"
    class="group flex h-full w-full min-w-0 cursor-pointer flex-col gap-4
           rounded-3xl border bg-fino-surface p-5 text-left shadow-sm
           transition-all duration-300
           hover:-translate-y-1 hover:shadow-md
           focus-visible:outline-2 focus-visible:outline-primary
           motion-reduce:transition-none motion-reduce:hover:translate-y-0"
    :class="cardStateClass"
    :aria-pressed="isSelected"
    @click="handleSelect"
  >
    <div class="flex items-start justify-between gap-3">
      <div
        class="flex size-12 shrink-0 items-center justify-center rounded-full
               text-base font-bold transition-all duration-300
               group-hover:scale-110 motion-reduce:group-hover:scale-100"
        :class="avatarStateClass"
        aria-hidden="true"
      >
        {{ persona.initials }}
      </div>

      <span
        class="shrink-0 rounded-lg bg-fino-surface-secondary px-2 py-1
               text-xs font-semibold text-fino-text"
      >
        {{ persona.code }}
      </span>
    </div>

    <div class="min-w-0">
      <p class="break-words text-base font-bold tracking-tight text-fino-text">
        {{ persona.fullName }}
      </p>

      <p class="mt-1 break-words text-sm text-fino-text-muted">
        {{ persona.organization }}
      </p>
    </div>

    <p
      class="mt-auto break-words border-t border-fino-border pt-4
             text-sm font-medium text-fino-text"
    >
      {{ persona.scenario }}
    </p>
  </button>
</template>
