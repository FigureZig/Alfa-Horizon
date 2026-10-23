<script setup lang="ts">
import { computed } from 'vue'
import Checkbox from 'primevue/checkbox'
import type {
  SandboxPersonaFlagGroupInterface,
  SandboxPersonaFlagInterface,
} from '@/app/types/sandbox/sandbox-persona-options-interface'

const props = defineProps<{
  groups: SandboxPersonaFlagGroupInterface[]
  flags: SandboxPersonaFlagInterface[]
  selected: string[]
  isDisabled: boolean
  // Особенности, которые называет причина в предпросмотре
  highlighted?: string[]
}>()

const emit = defineEmits<{
  change: [flagIds: string[]]
}>()

// Группы без подходящих форме флагов не показываем
const flagGroups = computed(() =>
  props.groups
    .map((group) => ({
      ...group,
      flags: props.flags.filter((flag) => flag.group === group.id),
    }))
    .filter((group) => group.flags.length),
)

function handleChange(flagIds: string[]) {
  emit('change', flagIds)
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <section
      v-for="group in flagGroups"
      :key="group.id"
      :aria-label="group.title"
    >
      <h4 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
        {{ group.title }}
      </h4>

      <ul class="mt-2 grid grid-cols-1 gap-2 xl:grid-cols-2">
        <li
          v-for="flag in group.flags"
          :key="flag.id"
        >
          <label
            :for="`persona-flag-${flag.id}`"
            class="flex h-full cursor-pointer items-start gap-3 rounded-2xl border p-3
                   transition-colors duration-200 hover:bg-fino-surface-hover
                   has-[:checked]:bg-fino-accent motion-reduce:transition-none"
            :class="highlighted?.includes(flag.id)
              ? 'border-primary ring-2 ring-primary/40'
              : 'border-fino-border has-[:checked]:border-primary'"
          >
            <Checkbox
              :model-value="selected"
              :input-id="`persona-flag-${flag.id}`"
              :value="flag.id"
              :disabled="isDisabled"
              class="mt-0.5 shrink-0"
              @update:model-value="handleChange"
            />

            <span class="min-w-0">
              <span class="block break-words text-sm font-semibold text-fino-text">
                {{ flag.title }}
              </span>

              <span class="mt-0.5 block break-words text-xs leading-relaxed text-fino-text-muted">
                {{ flag.effect }}
              </span>
            </span>
          </label>
        </li>
      </ul>
    </section>
  </div>
</template>
