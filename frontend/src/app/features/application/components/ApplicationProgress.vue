<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const STEPS = ['submitted', 'checking', 'decision', 'signing', 'issued'] as const
const STEP_ICONS: Record<(typeof STEPS)[number], string> = {
  submitted: 'pi pi-send',
  checking: 'pi pi-search',
  decision: 'pi pi-verified',
  signing: 'pi pi-pen-to-square',
  issued: 'pi pi-wallet',
}

const props = defineProps<{
  // Номер текущего шага: -1 — черновик, 5 — всё пройдено
  step: number
  // Что происходит внутри шага: «голосуют участники», «у специалиста»
  substep: string
}>()

const { t } = useI18n({ useScope: 'global' })

const lastIndex = STEPS.length - 1

// Заполнение шкалы: до центра текущего шага, после выдачи — целиком
const fillPercent = computed(() => {
  const reached = Math.min(Math.max(props.step, 0), lastIndex)

  return (reached / lastIndex) * 100
})

const isFinished = computed(() => props.step > lastIndex)

const currentLabel = computed(() => {
  if (isFinished.value) return t('application.progress.finished')
  if (props.step < 0) return t('application.progress.draft')

  return t('application.progress.current', {
    number: props.step + 1,
    total: STEPS.length,
    label: t(`application.progress.${STEPS[props.step]}`),
  })
})

const steps = computed(() =>
  STEPS.map((step, index) => {
    const isDone = index < props.step
    const isActive = index === props.step

    return {
      key: step,
      icon: STEP_ICONS[step],
      label: t(`application.progress.${step}`),
      substep: isActive ? props.substep : '',
      isDone,
      isActive,
      markerClass: isDone
        ? 'bg-primary text-primary-contrast'
        : isActive
          ? 'bg-fino-lime text-[#111] motion-safe:animate-pulse-ring scale-110'
          : 'bg-fino-surface text-fino-text-muted',
      labelClass: isActive
        ? 'bg-fino-line text-fino-surface px-2 py-0.5 rounded-md'
        : isDone ? 'text-fino-text' : 'text-fino-text-muted',
    }
  }),
)
</script>

<template>
  <div class="rounded-2xl border-2 border-fino-line bg-fino-surface-secondary p-4 sm:p-5">
    <p
      class="font-mono text-[11px] font-bold uppercase tracking-wider text-fino-text-muted"
      aria-live="polite"
    >
      {{ currentLabel }}
    </p>

    <div class="relative mt-4">
      <!-- Шкала за кружками: от центра первого шага до центра последнего, заливка едет пружиной к текущему -->
      <div
        class="pointer-events-none absolute top-[1.125rem] right-[10%] left-[10%] h-3 -translate-y-1/2 overflow-hidden
               rounded-full border-2 border-fino-line bg-fino-surface sm:top-6"
        aria-hidden="true"
      >
        <span
          class="block h-full bg-primary transition-[width] duration-700 ease-[cubic-bezier(0.2,1.2,0.4,1)]
                 motion-reduce:transition-none"
          :style="{ width: `${fillPercent}%` }"
        />
      </div>

      <ol
        class="relative grid grid-cols-5 gap-1"
        :aria-label="t('application.progress.label')"
      >
        <li
          v-for="(item, index) in steps"
          :key="item.key"
          class="relative flex min-w-0 flex-col items-center gap-2 text-center"
          :aria-current="item.isActive ? 'step' : undefined"
        >
          <span
            class="flex size-9 items-center justify-center rounded-full border-2 border-fino-line text-sm font-black
                   transition-[background-color,color,transform] duration-500 motion-reduce:transition-none sm:size-12"
            :class="item.markerClass"
          >
            <!-- key меняется вместе с состоянием: отметка «выстреливает» заново, когда шаг завершился -->
            <i
              v-if="item.isDone"
              :key="`${item.key}-done`"
              class="pi pi-check text-xs font-black motion-safe:animate-tick-pop sm:text-sm"
              aria-hidden="true"
            />
            <i
              v-else-if="item.isActive"
              :key="`${item.key}-active`"
              :class="item.icon"
              class="text-sm motion-safe:animate-tick-pop sm:text-base"
              aria-hidden="true"
            />
            <span
              v-else
              class="font-display"
            >
              {{ index + 1 }}
            </span>
          </span>

          <span class="flex w-full min-w-0 flex-col items-center">
            <span
              class="max-w-full truncate font-display text-[11px] font-extrabold transition-colors duration-300 sm:text-sm"
              :class="item.labelClass"
            >
              {{ item.label }}
            </span>

            <span
              v-if="item.substep"
              class="mt-1 text-[10px] leading-tight text-fino-text-muted sm:text-xs"
            >
              {{ item.substep }}
            </span>
          </span>
        </li>
      </ol>
    </div>
  </div>
</template>
