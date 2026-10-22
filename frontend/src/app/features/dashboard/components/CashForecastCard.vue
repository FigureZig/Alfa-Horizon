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

const hasCashGap = computed(() =>
  props.forecast.status === CashForecastStatusEnum.CashGap && Boolean(props.forecast.cashGap),
)

const title = computed(() => {
  const { cashGap, currency, horizonDays } = props.forecast

  if (hasCashGap.value && cashGap) {
    return t('cashForecast.gapTitle', {
      date: formatDate(cashGap.date, { day: 'numeric', month: 'long' }),
      amount: formatCurrency(cashGap.amount, currency),
    })
  }

  return t('cashForecast.healthyTitle', horizonDays)
})

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
        v-if="!hasCashGap"
        class="mt-1 text-sm text-fino-text-muted"
      >
        {{ t('cashForecast.healthyDescription') }}
      </p>
    </div>

    <CashForecastChart
      :points="forecast.points"
      :cash-gap="forecast.cashGap"
      :currency="forecast.currency"
    />

    <!-- Операции, которые приводят к дефициту -->
    <div
      v-if="hasCashGap && operations.length"
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
  </article>
</template>
