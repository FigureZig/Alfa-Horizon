<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CashForecastSection from '@/app/features/dashboard/components/CashForecastSection.vue'
import CompanyInsightsCard from '@/app/features/dashboard/components/CompanyInsightsCard.vue'
import DashboardApplicationCard from '@/app/features/dashboard/components/DashboardApplicationCard.vue'
import DashboardGreeting from '@/app/features/dashboard/components/DashboardGreeting.vue'
import DashboardGreetingSkeleton from '@/app/features/dashboard/components/DashboardGreetingSkeleton.vue'
import DashboardOffersCard from '@/app/features/dashboard/components/DashboardOffersCard.vue'
import DashboardTaskBanner from '@/app/features/dashboard/components/DashboardTaskBanner.vue'
import { useApplicationExplanation } from '@/app/composables/useApplicationExplanation'
import { useCashForecast } from '@/app/composables/useCashForecast'
import { useCompanyOverview } from '@/app/composables/useCompanyOverview'
import { useCompanyProducts } from '@/app/composables/useCompanyProducts'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFeatureFlags } from '@/app/composables/useFeatureFlags'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

// Заявка в работе у банка или у клиента: пока она идёт, конкурирующих предложений рядом не показываем
const ACTIVE_STATUSES: ApplicationDetailStatusEnum[] = [
  ApplicationDetailStatusEnum.Submitted,
  ApplicationDetailStatusEnum.Checking,
  ApplicationDetailStatusEnum.UnderReview,
  ApplicationDetailStatusEnum.InfoRequested,
  ApplicationDetailStatusEnum.Offered,
  ApplicationDetailStatusEnum.Signing,
  ApplicationDetailStatusEnum.Signed,
  ApplicationDetailStatusEnum.Disbursing,
]

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { isK1Enabled, isK2Enabled } = useFeatureFlags()

const { demoPersona, error: demoPersonaError, loadDemoPersona } = useDemoPersona()

// Прогноз денег (K1) и посчитанное под разрыв предложение (K2)
const {
  forecast,
  isForecastLoading,
  forecastError,
  isForecastDisabled,
  hasCashGap,
  loadForecast,
} = useCashForecast(() => (isK1Enabled ? props.inn : ''))

const {
  products,
  isProductsLoading,
  productsError,
  blockers,
  loadProducts,
} = useCompanyProducts(() => props.inn)

const {
  applicationsSummary,
  profile,
  isProfileLoading,
  profileError,
  loadProfile,
} = useCompanyOverview(() => props.inn)

const today = computed(() => demoPersona.value?.today ?? null)
const tasks = computed(() => applicationsSummary.value?.tasks ?? [])
const applications = computed(() => applicationsSummary.value?.applications ?? [])
const directors = computed(() => profile.value?.directors ?? [])

const isForecastVisible = computed(() => isK1Enabled && !isForecastDisabled.value)
const gapOffer = computed(() => (hasCashGap.value && isK2Enabled ? forecast.value?.offer ?? null : null))

// Заявки в работе: свежие сверху; те, по которым есть задача, уже стоят в полосе наверху
const activeApplications = computed(() =>
  applications.value
    .filter((application) => ACTIVE_STATUSES.includes(application.statusDetail))
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
)
const taskApplicationIds = computed(() => tasks.value.map((task) => task.applicationId))
const focusApplication = computed(() =>
  activeApplications.value.find((application) => !taskApplicationIds.value.includes(application.id)) ?? null,
)

// Справа — заявка в работе или предложения банка; если всё в работе уже в полосе задач, предложения не отвлекают
const isOffersVisible = computed(() => !activeApplications.value.length)

// Предложения без того, что уже стоит кнопкой в карточке денег
const offerProducts = computed(() =>
  products.value.filter((product) => product.code !== gapOffer.value?.code),
)

// Стоп-фактор: сколько банк даст после устранения причины — из пути к одобрению по последнему отказу
const rejectedApplicationId = computed(() => {
  if (!blockers.value.length) return null

  return applications.value
    .filter((application) => application.statusDetail === ApplicationDetailStatusEnum.Rejected)
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0]?.id ?? null
})
const { explanation: rejectedExplanation } = useApplicationExplanation(
  () => rejectedApplicationId.value ?? '',
  rejectedApplicationId,
)
const blockerFix = computed(() =>
  rejectedExplanation.value && !rejectedExplanation.value.pathBlocked
    ? rejectedExplanation.value.pathOptions[0] ?? null
    : null,
)

// «Оформить» предодобренный продукт: форма заявки открывается с его суммой и сроком
function applyForProduct(product: CreditProductInterface) {
  router.push({
    name: 'application-new',
    params: { inn: props.inn },
    query: {
      product: product.code,
      amount: product.amount,
      term: product.termMonths,
      ...(product.isRecommended ? { goal: CreditGoalEnum.CashGap } : {}),
    },
  })
}

function reloadDemoPersona() {
  loadDemoPersona(props.inn)
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <DashboardGreeting
      v-if="demoPersona"
      :first-name="demoPersona.firstName"
      :today="demoPersona.today"
      :organization-name="demoPersona.organizationName"
    />

    <AppErrorState
      v-else-if="demoPersonaError"
      :message="t('dashboard.personaLoadError')"
      @retry="reloadDemoPersona"
    />

    <DashboardGreetingSkeleton v-else />

    <!-- Главное дело — первым экраном: подписать, ответить банку, проголосовать -->
    <DashboardTaskBanner
      v-if="tasks.length"
      :inn="inn"
      :tasks="tasks"
      :applications="applications"
      :today="today"
    />

    <div
      class="grid grid-cols-1 items-start gap-6"
      :class="{ 'xl:grid-cols-[minmax(0,1fr)_22rem]': isForecastVisible && (focusApplication || isOffersVisible) }"
    >
      <!-- Что с деньгами: одна карточка, одно действие -->
      <CashForecastSection
        v-if="isForecastVisible"
        :inn="inn"
        :forecast="forecast"
        :offer="gapOffer"
        :is-loading="isForecastLoading"
        :has-error="forecastError"
        @retry="loadForecast"
      />

      <DashboardApplicationCard
        v-if="focusApplication"
        :inn="inn"
        :application-id="focusApplication.id"
        :product-name="focusApplication.productName"
        :more-count="activeApplications.length - 1"
        :directors="directors"
        :today="today"
      />

      <DashboardOffersCard
        v-else-if="isOffersVisible"
        :inn="inn"
        :products="offerProducts"
        :blockers="blockers"
        :fix="blockerFix"
        :rejected-application-id="rejectedApplicationId"
        :is-loading="isProductsLoading"
        :has-error="productsError"
        @apply="applyForProduct"
        @retry="loadProducts"
      />
    </div>

    <CompanyInsightsCard
      :profile="profile"
      :is-loading="isProfileLoading"
      :has-error="profileError"
      @retry="loadProfile"
    />
  </div>
</template>
