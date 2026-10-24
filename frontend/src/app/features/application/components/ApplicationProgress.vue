<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const STEPS = ['submitted', 'checking', 'decision', 'signing', 'issued'] as const

const props = defineProps<{
  // Номер текущего шага: -1 — черновик, 5 — всё пройдено
  step: number
  // Что происходит внутри шага: «голосуют участники», «у специалиста»
  substep: string
}>()

const { t } = useI18n({ useScope: 'global' })

const steps = computed(() =>
  STEPS.map((step, index) => {
    const isDone = index < props.step
    const isActive = index === props.step

    return {
      key: step,
      label: t(`application.progress.${step}`),
      substep: isActive ? props.substep : '',
      isDone,
      isActive,
      markerClass: isDone
        ? 'bg-primary text-primary-contrast'
        : isActive
          ? 'bg-fino-accent text-primary ring-2 ring-primary'
          : 'bg-fino-surface-secondary text-fino-text-muted',
      labelClass: isDone || isActive ? 'text-fino-text' : 'text-fino-text-muted',
    }
  }),
)
</script>

<template>
  <ol
    class="grid grid-cols-5 gap-1"
    :aria-label="t('application.progress.label')"
  >
    <li
      v-for="(item, index) in steps"
      :key="item.key"
      class="flex min-w-0 flex-col items-center gap-2 text-center"
      :aria-current="item.isActive ? 'step' : undefined"
    >
      <span
        class="flex size-8 items-center justify-center rounded-full text-xs font-bold
               transition-colors duration-300 motion-reduce:transition-none"
        :class="item.markerClass"
      >
        <i
          v-if="item.isDone"
          class="pi pi-check text-xs"
          aria-hidden="true"
        />
        <template v-else>
          {{ index + 1 }}
        </template>
      </span>

      <span class="flex w-full min-w-0 flex-col">
        <span
          class="truncate text-[11px] font-medium sm:text-xs"
          :class="item.labelClass"
        >
          {{ item.label }}
        </span>

        <span
          v-if="item.substep"
          class="mt-0.5 text-[10px] leading-tight text-fino-text-muted sm:text-[11px]"
        >
          {{ item.substep }}
        </span>
      </span>
    </li>
  </ol>
</template>
