<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import { HttpStatusCode, isAxiosError } from 'axios'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationsAndTasksCard from '@/app/features/dashboard/components/ApplicationsAndTasksCard.vue'
import CashForecastSection from '@/app/features/dashboard/components/CashForecastSection.vue'
import CompanyInsightsCard from '@/app/features/dashboard/components/CompanyInsightsCard.vue'
import DashboardGreeting from '@/app/features/dashboard/components/DashboardGreeting.vue'
import DashboardGreetingSkeleton from '@/app/features/dashboard/components/DashboardGreetingSkeleton.vue'
import FinanceStatCard from '@/app/features/dashboard/components/FinanceStatCard.vue'
import FinanceStatCardSkeleton from '@/app/features/dashboard/components/FinanceStatCardSkeleton.vue'
import PreApprovedProductsCard from '@/app/features/dashboard/components/PreApprovedProductsCard.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useCompanyOverview } from '@/app/composables/useCompanyOverview'
import { useCompanyProducts } from '@/app/composables/useCompanyProducts'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFeatureFlags } from '@/app/composables/useFeatureFlags'
import { useFormatters } from '@/app/composables/useFormatters'
import { dashboardService } from '@/app/services/dashboard/dashboard.service'
import { DashboardMapper } from '@/app/mappers/dashboard.mapper'
import { DashboardSummaryCardTypeEnum } from '@/app/types/dashboard/dashboard-summary-card-type-enum'
import type { AppLocale } from '@/app/i18n'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'
import type { DashboardSummaryCardInterface } from '@/app/types/dashboard/dashboard-summary-card-interface'

const SUMMARY_SKELETON_COUNT = 3
const DEFAULT_CARD_ICON = 'pi pi-chart-line'

const SUMMARY_CARD_ICONS: Record<DashboardSummaryCardTypeEnum, string> = {
  [DashboardSummaryCardTypeEnum.Balance]: 'pi pi-wallet',
  [DashboardSummaryCardTypeEnum.Outflow]: 'pi pi-arrow-up-right',
  [DashboardSummaryCardTypeEnum.Inflow]: 'pi pi-arrow-down-left',
}

const props = defineProps<{
  inn: string
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const $fetch = useApiFetch()
const toast = useToast()
const router = useRouter()
const { isK1Enabled } = useFeatureFlags()
const { formatCurrency } = useFormatters()

// Один запрос /products на страницу — его результат делят прогноз K1/K2 и «Предодобрено»
const {
  products,
  isProductsLoading,
  productsError,
  loadProducts,
} = useCompanyProducts(() => props.inn)

const {
  applicationsSummary,
  isApplicationsLoading,
  applicationsError,
  loadApplicationsSummary,
  profile,
  isProfileLoading,
  profileError,
  loadProfile,
} = useCompanyOverview(() => props.inn)
const {
  demoPersona,
  error: demoPersonaError,
  loadDemoPersona,
} = useDemoPersona()

const summaryCards = ref<DashboardSummaryCardInterface[]>([])
const isSummaryLoading = ref(false)
const summaryError = ref(false)

// Номер последнего запроса: ответ по предыдущей персоне не должен перезаписать текущую
let lastSummaryRequestId = 0

// Скелетоны только при первой загрузке: при смене языка карточки остаются на месте
const isSummarySkeletonVisible = computed(() => isSummaryLoading.value && !summaryCards.value.length)

// Пустой массив от бэкенда — блок карточек не показываем вовсе
const isSummaryVisible = computed(() =>
  isSummaryLoading.value || summaryError.value || summaryCards.value.length > 0,
)

const formattedSummaryCards = computed(() =>
  summaryCards.value.map((card) => ({
    id: card.id,
    title: card.title,
    value: formatCurrency(card.amount, card.currency),
    icon: SUMMARY_CARD_ICONS[card.type] ?? DEFAULT_CARD_ICON,
    description: card.description,
  })),
)

async function loadSummary() {
  const requestId = ++lastSummaryRequestId
  const inn = props.inn

  isSummaryLoading.value = true
  summaryError.value = false

  try {
    const { data } = await dashboardService.fetchSummary(
      $fetch,
      inn,
      locale.value as AppLocale,
    )

    if (requestId !== lastSummaryRequestId) return

    summaryCards.value = data.data.map((card) => DashboardMapper.toEntity(card))
  } catch (err: unknown) {
    if (requestId !== lastSummaryRequestId) return

    console.error('Dashboard summary loading failed:', err)
    summaryCards.value = []

    // Несуществующую персону обрабатывает загрузка её профиля (уведомление и возврат в /sandbox)
    if (isAxiosError(err) && err.response?.status === HttpStatusCode.NotFound) return

    summaryError.value = true

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.dashboardLoadError'),
      life: 4000,
    })
  } finally {
    if (requestId === lastSummaryRequestId) {
      isSummaryLoading.value = false
    }
  }
}

function onDemoPersonaChange() {
  // Карточки другой персоны сразу убираем, при смене языка оставляем до ответа
  summaryCards.value = []
  loadSummary()
}

function onLocaleChange() {
  loadSummary()
}

function applyForProduct(product: CreditProductInterface) {
  router.push({
    name: 'applications',
    params: { inn: props.inn },
    query: { productId: product.id },
  })
}

function retryDemoPersona() {
  loadDemoPersona(props.inn)
}

watch(() => props.inn, onDemoPersonaChange, { immediate: true })
watch(locale, onLocaleChange)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <!-- Приветствие -->
    <DashboardGreeting
      v-if="demoPersona"
      :first-name="demoPersona.firstName"
      :organization-name="demoPersona.organizationName"
    />

    <AppErrorState
      v-else-if="demoPersonaError"
      :message="t('dashboard.personaLoadError')"
      @retry="retryDemoPersona"
    />

    <DashboardGreetingSkeleton v-else />

    <!-- Финансовые карточки: количество и содержимое определяет бэкенд -->
    <section
      v-if="isSummaryVisible"
      :aria-label="t('dashboard.overview')"
    >
      <div
        v-if="isSummarySkeletonVisible"
        class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
        aria-busy="true"
      >
        <FinanceStatCardSkeleton
          v-for="index in SUMMARY_SKELETON_COUNT"
          :key="index"
        />
      </div>

      <AppErrorState
        v-else-if="summaryError"
        :message="t('dashboard.loadError')"
        @retry="loadSummary"
      />

      <div
        v-else
        class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      >
        <FinanceStatCard
          v-for="card in formattedSummaryCards"
          :key="card.id"
          :title="card.title"
          :value="card.value"
          :icon="card.icon"
          :description="card.description"
        />
      </div>
    </section>

    <!-- K1/K2: прогноз остатка и посчитанное кредитное предложение -->
    <CashForecastSection
      v-if="isK1Enabled"
      :inn="inn"
      :products="products"
      :is-products-loading="isProductsLoading"
      :products-error="productsError"
      @retry-products="loadProducts"
    />

    <!-- Сводка по компании: три независимых виджета -->
    <section
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      :aria-label="t('dashboard.companyOverview')"
    >
      <PreApprovedProductsCard
        :products="products"
        :is-loading="isProductsLoading"
        :has-error="productsError"
        @apply="applyForProduct"
        @retry="loadProducts"
      />

      <ApplicationsAndTasksCard
        :inn="inn"
        :summary="applicationsSummary"
        :is-loading="isApplicationsLoading"
        :has-error="applicationsError"
        @retry="loadApplicationsSummary"
      />

      <CompanyInsightsCard
        class="md:col-span-2 xl:col-span-1"
        :profile="profile"
        :is-loading="isProfileLoading"
        :has-error="profileError"
        @retry="loadProfile"
      />
    </section>
  </div>
</template>
