<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CreditHealthCardSkeleton from './CreditHealthCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { CreditScoreEffectEnum } from '@/app/types/company/credit-score-effect-enum'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { CreditScoreInterface } from '@/app/types/company/credit-score-interface'
import type { Nullable } from '@/app/types/nullable'

type FactorUnit = 'months' | 'percent' | 'days' | 'count' | 'rub'

// В каких единицах бэкенд отдаёт значение фактора скоринга
const FACTOR_UNITS: Record<string, FactorUnit> = {
  F1_business_age: 'months',
  F2_inflow_stability: 'percent',
  F3_inflow_trend: 'percent',
  F4_debt_load: 'percent',
  F5_delinquency: 'days',
  F6_credit_hunger: 'count',
  F7_tax_discipline: 'rub',
  F8_profitability: 'rub',
  F9_bank_share: 'percent',
}

const CLASS_TONES: Record<RiskClassEnum, string> = {
  [RiskClassEnum.A]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [RiskClassEnum.B]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [RiskClassEnum.C]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  [RiskClassEnum.D]: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

const props = defineProps<{
  creditScore: Nullable<CreditScoreInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.creditScore)

function formatFactorValue(factor: string, value: Nullable<number>): string {
  if (value === null) return t('credits.score.noData')

  switch (FACTOR_UNITS[factor]) {
    case 'months':
      return t('credits.score.unit.months', { value })
    case 'days':
      return t('credits.score.unit.days', { value })
    case 'percent':
      return formatPercent(value * 100)
    case 'rub':
      return formatCurrency(value, 'RUB')
    default:
      return String(value)
  }
}

const classChips = computed(() =>
  (props.creditScore?.classes ?? []).map((item) => ({
    riskClass: item.riskClass,
    min: t('credits.score.from', { min: item.min }),
    isCurrent: item.riskClass === props.creditScore?.riskClass,
  })),
)

const classTone = computed(() => (props.creditScore ? CLASS_TONES[props.creditScore.riskClass] : ''))

const factors = computed(() =>
  (props.creditScore?.factors ?? []).map((factor) => ({
    factor: factor.factor,
    title: factor.title,
    value: formatFactorValue(factor.factor, factor.value),
    points: factor.effect === CreditScoreEffectEnum.Unknown
      ? '—'
      : factor.points > 0 ? `+${factor.points}` : String(factor.points),
    pointsClass: factor.effect === CreditScoreEffectEnum.Plus
      ? 'text-green-700 dark:text-green-400'
      : factor.effect === CreditScoreEffectEnum.Minus
        ? 'text-red-700 dark:text-red-400'
        : 'text-fino-text-muted',
  })),
)

const levers = computed(() =>
  (props.creditScore?.levers ?? []).map((lever) => ({
    factor: lever.factor,
    title: lever.title,
    now: formatFactorValue(lever.factor, lever.value),
    goal: t(`credits.score.lever.${lever.way}`, { target: formatFactorValue(lever.factor, lever.target) }),
    gain: t('credits.score.gain', { gain: lever.gain }),
  })),
)

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
    :aria-label="t('credits.score.title')"
  >
    <div>
      <h2 class="text-sm font-semibold text-fino-text">
        {{ t('credits.score.title') }}
      </h2>

      <p class="mt-1 text-xs text-fino-text-muted">
        {{ t('credits.score.description') }}
      </p>
    </div>

    <CreditHealthCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('credits.score.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <template v-else-if="creditScore">
      <div class="flex items-center gap-4">
        <p class="text-5xl font-bold tracking-tight text-fino-text">
          {{ creditScore.score }}
        </p>

        <div>
          <span
            class="inline-flex rounded-lg px-2.5 py-1 text-xs font-semibold"
            :class="classTone"
          >
            {{ t('credits.score.riskClass', { riskClass: creditScore.riskClass }) }}
          </span>

          <p class="mt-1 text-xs text-fino-text-muted">
            {{ t('credits.score.points') }}
          </p>
        </div>
      </div>

      <ul class="grid grid-cols-4 gap-2">
        <li
          v-for="chip in classChips"
          :key="chip.riskClass"
          class="rounded-xl border px-2 py-2 text-center"
          :class="chip.isCurrent ? 'border-primary bg-fino-accent' : 'border-fino-border'"
          :aria-current="chip.isCurrent ? 'true' : undefined"
        >
          <p class="text-sm font-bold text-fino-text">
            {{ chip.riskClass }}
          </p>

          <p class="text-[11px] text-fino-text-muted">
            {{ chip.min }}
          </p>
        </li>
      </ul>

      <p
        v-if="creditScore.hasMissingFactors"
        class="flex items-start gap-2 rounded-2xl bg-fino-surface-secondary p-3 text-xs text-fino-text-muted"
      >
        <i
          class="pi pi-info-circle mt-0.5"
          aria-hidden="true"
        />
        {{ creditScore.bkiKnown ? t('credits.score.missingFactors') : t('credits.score.noBki') }}
      </p>

      <div>
        <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ t('credits.score.factors') }}
        </h3>

        <ul class="mt-2 flex flex-col divide-y divide-fino-border">
          <li
            v-for="factor in factors"
            :key="factor.factor"
            class="flex items-start justify-between gap-3 py-2 text-sm first:pt-0 last:pb-0"
          >
            <div class="min-w-0">
              <p class="break-words text-fino-text">
                {{ factor.title }}
              </p>

              <p class="text-xs text-fino-text-muted">
                {{ factor.value }}
              </p>
            </div>

            <span
              class="shrink-0 font-semibold"
              :class="factor.pointsClass"
            >
              {{ factor.points }}
            </span>
          </li>
        </ul>
      </div>

      <div v-if="levers.length">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ t('credits.score.levers') }}
        </h3>

        <ul class="mt-2 flex flex-col gap-2">
          <li
            v-for="lever in levers"
            :key="lever.factor"
            class="rounded-xl bg-fino-surface-secondary p-3 text-sm"
          >
            <div class="flex items-start justify-between gap-3">
              <p class="min-w-0 break-words font-semibold text-fino-text">
                {{ lever.title }}
              </p>

              <span class="shrink-0 font-semibold text-green-700 dark:text-green-400">
                {{ lever.gain }}
              </span>
            </div>

            <p class="mt-0.5 break-words text-xs text-fino-text-muted">
              {{ t('credits.score.leverNow', { now: lever.now, goal: lever.goal }) }}
            </p>
          </li>
        </ul>
      </div>
    </template>
  </article>
</template>
