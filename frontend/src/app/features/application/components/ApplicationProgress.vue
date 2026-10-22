<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'

const STEPS = ['submitted', 'checking', 'decision', 'signing', 'issued'] as const

// Номер шага, на котором сейчас заявка (статусы дозапроса и ручного рассмотрения — это всё ещё проверка)
const STATUS_STEP: Partial<Record<ApplicationDetailStatusEnum, number>> = {
  [ApplicationDetailStatusEnum.Draft]: -1,
  [ApplicationDetailStatusEnum.Submitted]: 0,
  [ApplicationDetailStatusEnum.Checking]: 1,
  [ApplicationDetailStatusEnum.InfoRequested]: 1,
  [ApplicationDetailStatusEnum.UnderReview]: 1,
  [ApplicationDetailStatusEnum.Offered]: 2,
  [ApplicationDetailStatusEnum.Signing]: 3,
  [ApplicationDetailStatusEnum.Signed]: 4,
  [ApplicationDetailStatusEnum.Disbursing]: 4,
  [ApplicationDetailStatusEnum.Issued]: 5,
}

const props = defineProps<{
  status: ApplicationDetailStatusEnum
}>()

const { t } = useI18n({ useScope: 'global' })

const currentStep = computed(() => STATUS_STEP[props.status])

// Для отказа, отзыва и истёкших сроков линейный путь не показываем
const isVisible = computed(() => currentStep.value !== undefined)

const steps = computed(() =>
  STEPS.map((step, index) => {
    const current = currentStep.value ?? -1
    const isDone = index < current
    const isActive = index === current

    return {
      key: step,
      label: t(`application.progress.${step}`),
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
    v-if="isVisible"
    class="grid grid-cols-5 gap-1"
    :aria-label="t('application.progress.label')"
  >
    <li
      v-for="(step, index) in steps"
      :key="step.key"
      class="flex min-w-0 flex-col items-center gap-2 text-center"
      :aria-current="step.isActive ? 'step' : undefined"
    >
      <span
        class="flex size-8 items-center justify-center rounded-full text-xs font-bold
               transition-colors duration-300 motion-reduce:transition-none"
        :class="step.markerClass"
      >
        <i
          v-if="step.isDone"
          class="pi pi-check text-xs"
          aria-hidden="true"
        />
        <template v-else>
          {{ index + 1 }}
        </template>
      </span>

      <span
        class="w-full truncate text-[11px] font-medium sm:text-xs"
        :class="step.labelClass"
      >
        {{ step.label }}
      </span>
    </li>
  </ol>
</template>
