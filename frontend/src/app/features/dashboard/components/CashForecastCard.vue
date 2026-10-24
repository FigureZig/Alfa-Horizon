<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import CashForecastChart from './CashForecastChart.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import type { CashForecastInterface, CashGapOfferInterface } from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

// Сколько спишется и поступит до даты разрыва: карточки сводки бэкенда
interface CashFlowInterface {
  id: string
  title: string
  value: string
  description: string
  isOutflow: boolean
}

const props = defineProps<{
  forecast: CashForecastInterface
  // Предложение под разрыв: его цена — главное действие карточки
  offer: Nullable<CashGapOfferInterface>
  flows: CashFlowInterface[]
}>()

const emit = defineEmits<{
  closeGap: []
  showOptions: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDate, formatPercent } = useFormatters()

const isCovered = computed(() => props.forecast.status === CashForecastStatusEnum.Covered)
const hasCashGap = computed(() =>
  props.forecast.status === CashForecastStatusEnum.CashGap && Boolean(props.forecast.cashGap),
)
const hasShortfall = computed(() => (hasCashGap.value || isCovered.value) && Boolean(props.forecast.cashGap))

function formatAmount(value: number): string {
  return formatCurrency(value, props.forecast.currency)
}

// Сколько на счёте сейчас — первая точка прогноза
const balanceNow = computed(() => {
  const today = props.forecast.points[0]

  return today ? formatAmount(today.balance) : ''
})

const title = computed(() => {
  const { cashGap, horizonDays } = props.forecast

  if (hasShortfall.value && cashGap) {
    const params = { date: formatDate(cashGap.date, { day: 'numeric', month: 'long' }), amount: formatAmount(cashGap.amount) }

    return t(isCovered.value ? 'cashForecast.coveredTitle' : 'cashForecast.gapTitle', params)
  }

  return t('cashForecast.healthyTitle', horizonDays)
})

// Цена закрытия разрыва — крупнее лимита: человеку нужна недостающая сумма, а не весь лимит
const description = computed(() => {
  const { creditLine } = props.forecast

  if (isCovered.value) {
    return creditLine
      ? t('cashForecast.coveredDescription', { limit: formatAmount(creditLine) })
      : t('cashForecast.coveredDescriptionNoLimit')
  }

  if (!hasCashGap.value) return t('cashForecast.healthyDescription')

  const cover = props.offer?.cover

  return cover
    ? t('cashForecast.gapCover', {
      amount: formatAmount(cover.amount),
      days: t('cashForecast.days', cover.days),
      interest: formatAmount(cover.interest),
    })
    : t('cashForecast.gapNoOffer')
})

const offerLine = computed(() => {
  const offer = props.offer

  return offer
    ? t('cashForecast.offerLine', { name: offer.name, limit: formatAmount(offer.amount), rate: formatPercent(offer.rate) })
    : ''
})

const closeGapLabel = computed(() => {
  const interest = props.offer?.cover?.interest

  return interest !== undefined
    ? t('cashForecast.closeGapFor', { interest: formatAmount(interest) })
    : t('cashForecast.closeGap')
})

const operations = computed(() =>
  props.forecast.operations.map((operation) => ({
    id: operation.id,
    date: formatDate(operation.date, { day: 'numeric', month: 'short' }),
    title: operation.title,
    amount: formatAmount(operation.amount),
  })),
)

const dailyInflow = computed(() =>
  props.forecast.dailyInflow !== null
    ? t('cashForecast.dailyInflow', { amount: formatAmount(props.forecast.dailyInflow) })
    : '',
)

const outflows = computed(() =>
  props.forecast.regularOutflows.map((outflow) => ({
    key: `${outflow.day}-${outflow.title}`,
    day: t('cashForecast.outflowDay', { day: outflow.day }),
    title: outflow.title,
    amount: formatAmount(outflow.amount),
  })),
)

const hasFlows = computed(() => props.flows.length > 0 || operations.value.length > 0)

function handleCloseGap() {
  emit('closeGap')
}

function handleShowOptions() {
  emit('showOptions')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-5 card-key p-5 sm:p-6"
  >
    <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <span class="text-sm text-fino-text-muted">
        {{ t('cashForecast.subtitle', forecast.horizonDays) }}
      </span>

      <span
        v-if="balanceNow"
        class="text-sm text-fino-text-muted"
      >
        {{ t('cashForecast.balanceNow') }}
        <span class="font-semibold text-fino-text">{{ balanceNow }}</span>
      </span>
    </div>

    <div>
      <h2 class="flex items-start gap-2 break-words text-xl font-display font-black text-fino-text sm:text-2xl">
        <i
          v-if="hasCashGap"
          class="pi pi-exclamation-circle mt-1 text-lg text-red-600 dark:text-red-400"
          aria-hidden="true"
        />
        <i
          v-else
          class="pi pi-check-circle mt-1 text-lg text-green-600 dark:text-green-400"
          aria-hidden="true"
        />
        {{ title }}
      </h2>

      <p class="mt-1.5 text-sm leading-relaxed text-fino-text-muted sm:text-base">
        {{ description }}
      </p>
    </div>

    <!-- Одно действие: закрыть разрыв по посчитанной цене -->
    <div
      v-if="hasCashGap"
      class="flex flex-col gap-3"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
        <button
          v-if="offer"
          type="button"
          class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
                 font-semibold text-primary-contrast focus-visible:outline-2 focus-visible:outline-offset-2
                 focus-visible:outline-primary btn-key"
          @click="handleCloseGap"
        >
          <i
            class="pi pi-bolt text-xs"
            aria-hidden="true"
          />
          {{ closeGapLabel }}
        </button>

        <button
          type="button"
          class="inline-flex min-h-12 cursor-pointer items-center justify-center rounded-xl px-5 text-sm font-semibold
                 transition-colors duration-200 motion-reduce:transition-none
                 focus-visible:outline-2 focus-visible:outline-primary"
          :class="offer
            ? 'text-fino-text-muted hover:bg-fino-surface-hover hover:text-fino-text'
            : 'bg-primary text-primary-contrast hover:opacity-90'"
          @click="handleShowOptions"
        >
          {{ offer ? t('cashForecast.otherOptions') : t('cashForecast.findCredit') }}
        </button>
      </div>

      <p
        v-if="offerLine"
        class="text-xs text-fino-text-muted"
      >
        {{ offerLine }}
      </p>
    </div>

    <CashForecastChart
      :points="forecast.points"
      :cash-gap="forecast.cashGap"
      :currency="forecast.currency"
    />

    <div class="flex flex-col gap-2">
      <!-- Что спишется и поступит: подробности по запросу -->
      <details
        v-if="hasFlows"
        class="group rounded-2xl border border-fino-border"
      >
        <summary
          class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                 text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
        >
          {{ t('cashForecast.flowsTitle') }}
          <i
            class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                   group-open:rotate-180 motion-reduce:transition-none"
            aria-hidden="true"
          />
        </summary>

        <div class="flex flex-col gap-4 px-4 pb-4">
          <dl
            v-if="flows.length"
            class="grid grid-cols-1 gap-3 sm:grid-cols-2"
          >
            <div
              v-for="flow in flows"
              :key="flow.id"
              class="min-w-0 rounded-xl bg-fino-surface-secondary p-3"
            >
              <dt class="text-xs text-fino-text-muted">
                {{ flow.title }}
              </dt>
              <dd
                class="mt-1 text-lg font-bold tracking-tight"
                :class="flow.isOutflow ? 'text-fino-text' : 'text-green-700 dark:text-green-400'"
              >
                {{ flow.value }}
              </dd>
              <dd class="mt-0.5 break-words text-xs text-fino-text-muted">
                {{ flow.description }}
              </dd>
            </div>
          </dl>

          <div v-if="operations.length">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
              {{ hasShortfall ? t('cashForecast.operationsTitle') : t('cashForecast.upcomingTitle') }}
            </h3>

            <ul class="mt-1 flex flex-col divide-y divide-fino-border">
              <li
                v-for="operation in operations"
                :key="operation.id"
                class="flex items-center gap-3 py-2.5 text-sm"
              >
                <span class="w-14 shrink-0 text-fino-text-muted">{{ operation.date }}</span>
                <span class="min-w-0 flex-1 break-words text-fino-text">{{ operation.title }}</span>
                <span class="shrink-0 font-semibold whitespace-nowrap text-fino-text">{{ operation.amount }}</span>
              </li>
            </ul>
          </div>
        </div>
      </details>

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
              <span class="w-24 shrink-0 whitespace-nowrap text-fino-text-muted">{{ outflow.day }}</span>
              <span class="min-w-0 flex-1 break-words text-fino-text">{{ outflow.title }}</span>
              <span class="shrink-0 font-semibold whitespace-nowrap text-fino-text">{{ outflow.amount }}</span>
            </li>
          </ul>
        </div>
      </details>
    </div>
  </article>
</template>
