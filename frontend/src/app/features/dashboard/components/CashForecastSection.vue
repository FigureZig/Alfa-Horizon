<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CashForecastCard from './CashForecastCard.vue'
import CashForecastCardSkeleton from './CashForecastCardSkeleton.vue'
import CloseGapDialog from './CloseGapDialog.vue'
import CompanyContractCard from './CompanyContractCard.vue'
import CreditOfferCard from './CreditOfferCard.vue'
import { useApplicationCreate } from '@/app/composables/useApplicationCreate'
import { useCashForecast } from '@/app/composables/useCashForecast'
import { useFeatureFlags } from '@/app/composables/useFeatureFlags'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()

const { isK2Enabled } = useFeatureFlags()
const {
  forecast,
  isForecastLoading,
  forecastError,
  isForecastDisabled,
  hasCashGap,
  loadForecast,
} = useCashForecast(() => props.inn)
const { isSubmitting, errorMessage, createAndSubmit } = useApplicationCreate(props.inn)

const isCloseGapVisible = ref(false)

// Кредит предлагаем, только если K1 нашёл разрыв, а K2 посчитал предложение под него
const offer = computed(() => (hasCashGap.value && isK2Enabled ? forecast.value?.offer ?? null : null))

const contract = computed(() => forecast.value?.contract ?? null)

const isForecastSkeletonVisible = computed(() => isForecastLoading.value && !forecast.value)

// Колонка предложения нужна только при разрыве; без предложения график занимает всю ширину
const isOfferVisible = computed(() => Boolean(offer.value))

function openCloseGap() {
  isCloseGapVisible.value = true
}

function handleCloseGapVisibleChange(visible: boolean) {
  isCloseGapVisible.value = visible
}

// Одно подтверждение с ценой: заявка создаётся и подаётся, дальше — страница заявки
async function confirmCloseGap(consentBki: boolean) {
  const current = offer.value

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

function showCreditOptions() {
  router.push({ name: 'credits', params: { inn: props.inn } })
}
</script>

<template>
  <section
    v-if="!isForecastDisabled"
    class="flex flex-col gap-4"
    :aria-label="t('cashForecast.sectionLabel')"
  >
    <div
      class="grid grid-cols-1 items-stretch gap-4"
      :class="{ 'xl:grid-cols-[minmax(0,1fr)_22rem]': isOfferVisible }"
    >
      <!-- K1: прогноз остатка -->
      <CashForecastCardSkeleton v-if="isForecastSkeletonVisible" />

      <AppErrorState
        v-else-if="forecastError"
        :message="t('cashForecast.loadError')"
        @retry="loadForecast"
      />

      <CashForecastCard
        v-else-if="forecast"
        :forecast="forecast"
      />

      <div
        v-else
        class="flex flex-col items-center rounded-3xl border border-dashed
               border-fino-border bg-fino-surface px-6 py-10 text-center"
      >
        <div class="flex size-12 items-center justify-center rounded-2xl bg-fino-accent text-primary">
          <i
            class="pi pi-chart-line text-xl"
            aria-hidden="true"
          />
        </div>

        <p class="mt-4 max-w-sm text-sm text-fino-text-muted">
          {{ t('cashForecast.empty') }}
        </p>
      </div>

      <!-- K2: предложение под разрыв -->
      <CreditOfferCard
        v-if="offer"
        :offer="offer"
        @close-gap="openCloseGap"
        @show-options="showCreditOptions"
      />
    </div>

    <!-- K5: госконтракт -->
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
