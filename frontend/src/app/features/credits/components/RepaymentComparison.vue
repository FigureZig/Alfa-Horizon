<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import RepaymentComparisonSkeleton from './RepaymentComparisonSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { RepaymentRecommendationEnum } from '@/app/types/company/repayment-recommendation-enum'
import type { RepaymentInterface } from '@/app/types/company/repayment-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  repayment: Nullable<RepaymentInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.repayment)

const options = computed(() => {
  const repayment = props.repayment

  if (!repayment) return []

  const isFixedRecommended = repayment.recommendation === RepaymentRecommendationEnum.Fixed

  return [
    {
      key: RepaymentRecommendationEnum.Fixed,
      isRecommended: isFixedRecommended,
      title: t('credits.repayment.fixed.title'),
      description: t('credits.repayment.fixed.description'),
      lines: [
        { label: t('credits.repayment.fixed.payment'), value: formatCurrency(repayment.fixedPayment, 'RUB') },
        { label: t('credits.repayment.interest'), value: formatCurrency(repayment.fixedTotalInterest, 'RUB') },
        {
          label: t('credits.repayment.fixed.stress'),
          value: formatPercent(repayment.fixedWorstShare * 100),
        },
      ],
      note: repayment.isFixedComfortable
        ? t('credits.repayment.fixed.comfortable')
        : t('credits.repayment.fixed.uncomfortable'),
      isNoteGood: repayment.isFixedComfortable,
    },
    {
      key: RepaymentRecommendationEnum.FromInflows,
      isRecommended: !isFixedRecommended,
      title: t('credits.repayment.inflows.title'),
      description: t('credits.repayment.inflows.description', { share: formatPercent(repayment.inflowShare * 100) }),
      lines: [
        {
          label: t('credits.repayment.inflows.payment'),
          value: `${formatCurrency(repayment.inflowMinPayment, 'RUB')} – ${formatCurrency(repayment.inflowMaxPayment, 'RUB')}`,
        },
        { label: t('credits.repayment.interest'), value: formatCurrency(repayment.inflowTotalInterest, 'RUB') },
        { label: t('credits.repayment.inflows.months'), value: t('credits.repayment.inflows.monthsValue', repayment.inflowMonths) },
      ],
      note: '',
      isNoteGood: true,
    },
  ]
})

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <section
    class="flex flex-col gap-4"
    :aria-label="t('credits.repayment.title')"
  >
    <div>
      <h3 class="text-base font-bold tracking-tight text-fino-text">
        {{ t('credits.repayment.title') }}
      </h3>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('credits.repayment.description') }}
      </p>
    </div>

    <RepaymentComparisonSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('credits.repayment.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <template v-else-if="repayment">
      <p
        v-if="repayment.why"
        class="flex items-start gap-2 rounded-2xl bg-fino-accent p-3 text-sm text-fino-text"
      >
        <i
          class="pi pi-lightbulb mt-0.5 text-primary"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ repayment.why }}</span>
      </p>

      <ul class="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <li
          v-for="option in options"
          :key="option.key"
          class="flex min-w-0 flex-col gap-3 rounded-2xl border p-4"
          :class="option.isRecommended ? 'border-primary' : 'border-fino-border'"
        >
          <div class="flex items-start justify-between gap-3">
            <p class="min-w-0 break-words text-sm font-semibold text-fino-text">
              {{ option.title }}
            </p>

            <span
              v-if="option.isRecommended"
              class="shrink-0 rounded-md bg-primary px-2 py-0.5 text-[11px] font-semibold text-primary-contrast"
            >
              {{ t('credits.repayment.recommended') }}
            </span>
          </div>

          <p class="text-xs leading-relaxed text-fino-text-muted">
            {{ option.description }}
          </p>

          <dl class="flex flex-col gap-1.5 text-sm">
            <div
              v-for="line in option.lines"
              :key="line.label"
              class="flex justify-between gap-3"
            >
              <dt class="text-fino-text-muted">
                {{ line.label }}
              </dt>
              <dd class="break-words text-right font-semibold text-fino-text">
                {{ line.value }}
              </dd>
            </div>
          </dl>

          <p
            v-if="option.note"
            class="text-xs font-semibold"
            :class="option.isNoteGood ? 'text-green-700 dark:text-green-400' : 'text-red-700 dark:text-red-400'"
          >
            {{ option.note }}
          </p>
        </li>
      </ul>
    </template>
  </section>
</template>
