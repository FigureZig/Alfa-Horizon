<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CashForecastChart from './CashForecastChart.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import type { CashForecastInterface } from '@/app/types/company/cash-forecast-interface'

const props = defineProps<{
  forecast: CashForecastInterface
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDate } = useFormatters()

// Минус покрыт овердрафтом: это не разрыв, а спокойное «уйдёте в минус — лимит покроет»
const isCovered = computed(() => props.forecast.status === CashForecastStatusEnum.Covered)

const hasCashGap = computed(() =>
  props.forecast.status === CashForecastStatusEnum.CashGap && Boolean(props.forecast.cashGap),
)

const hasShortfall = computed(() => (hasCashGap.value || isCovered.value) && Boolean(props.forecast.cashGap))

const title = computed(() => {
  const { cashGap, currency, horizonDays } = props.forecast

  if (hasShortfall.value && cashGap) {
    const params = {
      date: formatDate(cashGap.date, { day: 'numeric', month: 'long' }),
      amount: formatCurrency(cashGap.amount, currency),
    }

    return t(isCovered.value ? 'cashForecast.coveredTitle' : 'cashForecast.gapTitle', params)
  }

  return t('cashForecast.healthyTitle', horizonDays)
})

const description = computed(() => {
  const { creditLine, currency } = props.forecast

  if (isCovered.value) {
    return creditLine
      ? t('cashForecast.coveredDescription', { limit: formatCurrency(creditLine, currency) })
      : t('cashForecast.coveredDescriptionNoLimit')
  }

  return hasCashGap.value ? '' : t('cashForecast.healthyDescription')
})

const outflows = computed(() =>
  props.forecast.regularOutflows.map((outflow) => ({
    key: `${outflow.day}-${outflow.title}`,
    day: t('cashForecast.outflowDay', { day: outflow.day }),
    title: outflow.title,
    amount: formatCurrency(outflow.amount, props.forecast.currency),
  })),
)

const dailyInflow = computed(() =>
  props.forecast.dailyInflow !== null
    ? t('cashForecast.dailyInflow', { amount: formatCurrency(props.forecast.dailyInflow, props.forecast.currency) })
    : '',
)

const operations = computed(() =>
  props.forecast.operations.map((operation) => ({
    id: operation.id,
    date: formatDate(operation.date, { day: 'numeric', month: 'short' }),
    title: operation.title,
    amount: formatCurrency(operation.amount, props.forecast.currency),
  })),
)
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm sm:p-6"
  >
    <!-- Шапка -->
    <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
      <span
        class="inline-flex items-center gap-1.5 rounded-full bg-fino-accent
               px-3 py-1 text-xs font-semibold text-primary"
      >
        <i
          class="pi pi-eye text-xs"
          aria-hidden="true"
        />
        {{ t('cashForecast.badge') }}
      </span>

      <span class="text-sm text-fino-text-muted">
        {{ t('cashForecast.subtitle', forecast.horizonDays) }}
      </span>
    </div>

    <!-- Заголовок -->
    <div>
      <h2
        class="flex items-start gap-2 break-words text-xl font-bold tracking-tight
               text-fino-text sm:text-2xl"
      >
        <i
          v-if="!hasCashGap"
          class="pi pi-check-circle mt-1 text-lg text-green-600 dark:text-green-400"
          aria-hidden="true"
        />
        {{ title }}
      </h2>

      <p
        v-if="description"
        class="mt-1 text-sm text-fino-text-muted"
      >
        {{ description }}
      </p>
    </div>

    <CashForecastChart
      :points="forecast.points"
      :cash-gap="forecast.cashGap"
      :currency="forecast.currency"
    />

    <!-- Операции, которые приводят к дефициту -->
    <div
      v-if="hasShortfall && operations.length"
      class="border-t border-fino-border pt-4"
    >
      <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
        {{ t('cashForecast.operationsTitle') }}
      </h3>

      <ul class="mt-2 flex flex-col divide-y divide-fino-border">
        <li
          v-for="operation in operations"
          :key="operation.id"
          class="flex items-center gap-3 py-2.5 text-sm"
        >
          <span class="w-14 shrink-0 text-fino-text-muted">
            {{ operation.date }}
          </span>

          <span class="min-w-0 flex-1 break-words text-fino-text">
            {{ operation.title }}
          </span>

          <span class="shrink-0 font-semibold whitespace-nowrap text-fino-text">
            {{ operation.amount }}
          </span>
        </li>
      </ul>
    </div>

    <!-- Как посчитали: подробности по запросу -->
    <details
      v-if="dailyInflow || outflows.length"
      class="group rounded-2xl border border-fino-border"
    >
      <summary
        class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
               text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
      >
        {{ t('cashForecast.howTitle') }}
        <i
          class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                 group-open:rotate-180 motion-reduce:transition-none"
          aria-hidden="true"
        />
      </summary>

      <div class="px-4 pb-4">
        <p
          v-if="dailyInflow"
          class="text-sm text-fino-text-muted"
        >
          {{ dailyInflow }}
        </p>

        <ul class="mt-2 flex flex-col divide-y divide-fino-border">
          <li
            v-for="outflow in outflows"
            :key="outflow.key"
            class="flex items-center gap-3 py-2 text-sm"
          >
            <span class="w-20 shrink-0 text-fino-text-muted">{{ outflow.day }}</span>
            <span class="min-w-0 flex-1 break-words text-fino-text">{{ outflow.title }}</span>
            <span class="shrink-0 font-semibold whitespace-nowrap text-fino-text">{{ outflow.amount }}</span>
          </li>
        </ul>
      </div>
    </details>
  </article>
</template>
