<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CashForecastCard from './CashForecastCard.vue'
import CashForecastCardSkeleton from './CashForecastCardSkeleton.vue'
import CloseGapDialog from './CloseGapDialog.vue'
import CompanyContractCard from './CompanyContractCard.vue'
import { useApplicationCreate } from '@/app/composables/useApplicationCreate'
import { useDashboardSummary } from '@/app/composables/useDashboardSummary'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import { DashboardSummaryCardTypeEnum } from '@/app/types/dashboard/dashboard-summary-card-type-enum'
import type { CashForecastInterface, CashGapOfferInterface } from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

const FLOW_TYPES = [DashboardSummaryCardTypeEnum.Outflow, DashboardSummaryCardTypeEnum.Inflow]

const props = defineProps<{
  inn: string
  forecast: Nullable<CashForecastInterface>
  // Предложение под разрыв, если банк его посчитал
  offer: Nullable<CashGapOfferInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()

const { isSubmitting, errorMessage, createAndSubmit } = useApplicationCreate(props.inn)
// Сколько спишется и поступит до даты разрыва — свёрнуто в карточке денег
const { cards } = useDashboardSummary(() => props.inn)

const isCloseGapVisible = ref(false)

const flows = computed(() =>
  cards.value
    .filter((card) => FLOW_TYPES.includes(card.type))
    .map((card) => ({
      id: card.id,
      title: card.title,
      value: card.value,
      description: card.description,
      isOutflow: card.type === DashboardSummaryCardTypeEnum.Outflow,
    })),
)

const contract = computed(() => props.forecast?.contract ?? null)
const isSkeletonVisible = computed(() => props.isLoading && !props.forecast)

function openCloseGap() {
  isCloseGapVisible.value = true
}

function handleCloseGapVisibleChange(visible: boolean) {
  isCloseGapVisible.value = visible
}

// Одно подтверждение с ценой: заявка создаётся и подаётся, дальше — страница заявки
async function confirmCloseGap(consentBki: boolean) {
  const current = props.offer

  if (!current) return

  const application = await createAndSubmit({
    product: current.code,
    amount: current.amount,
    termMonths: current.termMonths,
    goal: CreditGoalEnum.CashGap,
    consentBki,
  })

  if (!application) return

  isCloseGapVisible.value = false
  await router.push({ name: 'application', params: { inn: props.inn, applicationId: application.id } })
}

// Без посчитанного предложения — подбор сразу с задачей «закрыть разрыв»
function showCreditOptions() {
  router.push({ name: 'credits', params: { inn: props.inn }, query: { goal: CreditGoalEnum.CashGap } })
}

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <section
    class="flex min-w-0 flex-col gap-4"
    :aria-label="t('cashForecast.sectionLabel')"
  >
    <CashForecastCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('cashForecast.loadError')"
      @retry="handleRetry"
    />

    <CashForecastCard
      v-else-if="forecast"
      :forecast="forecast"
      :offer="offer"
      :flows="flows"
      @close-gap="openCloseGap"
      @show-options="showCreditOptions"
    />

    <div
      v-else
      class="flex flex-col items-center rounded-3xl border border-dashed
             border-fino-border bg-fino-surface px-6 py-10 text-center"
    >
      <div class="flex size-12 items-center justify-center rounded-2xl bg-fino-accent text-primary border-2 border-fino-line">
        <i
          class="pi pi-chart-line text-xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 max-w-sm text-sm text-fino-text-muted">
        {{ t('cashForecast.empty') }}
      </p>
    </div>

    <!-- Госконтракт: под него банк даёт кредит на исполнение -->
    <CompanyContractCard
      v-if="contract"
      :inn="inn"
      :contract="contract"
    />

    <CloseGapDialog
      v-if="offer"
      :visible="isCloseGapVisible"
      :offer="offer"
      :gap="forecast?.cashGap ?? null"
      :is-submitting="isSubmitting"
      :error-message="errorMessage"
      @update:visible="handleCloseGapVisibleChange"
      @confirm="confirmCloseGap"
    />
  </section>
</template>
