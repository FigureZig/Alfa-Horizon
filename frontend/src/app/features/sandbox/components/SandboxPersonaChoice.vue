<script setup lang="ts">
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaChoiceInterface } from '@/app/types/sandbox/sandbox-persona-options-interface'

defineProps<{
  options: SandboxPersonaChoiceInterface[]
  modelValue: Nullable<string>
  label: string
  isDisabled: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function handleSelect(value: string) {
  emit('update:modelValue', value)
}
</script>

<template>
  <div
    class="flex flex-wrap gap-2"
    role="radiogroup"
    :aria-label="label"
  >
    <button
      v-for="option in options"
      :key="option.id"
      type="button"
      role="radio"
      class="min-h-10 cursor-pointer rounded-xl border px-3.5 py-2 text-left text-sm font-medium
             transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-primary
             disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none"
      :class="option.id === modelValue
        ? 'border-primary bg-fino-accent text-primary'
        : 'border-fino-border bg-fino-surface text-fino-text hover:bg-fino-surface-hover'"
      :aria-checked="option.id === modelValue"
      :disabled="isDisabled"
      @click="handleSelect(option.id)"
    >
      {{ option.title }}
    </button>
  </div>
</template>
