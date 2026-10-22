<script setup lang="ts">
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationsAndTasksCard from '@/app/features/dashboard/components/ApplicationsAndTasksCard.vue'
import CashForecastSection from '@/app/features/dashboard/components/CashForecastSection.vue'
import CompanyInsightsCard from '@/app/features/dashboard/components/CompanyInsightsCard.vue'
import DashboardSummarySection from '@/app/features/dashboard/components/DashboardSummarySection.vue'
import DashboardGreeting from '@/app/features/dashboard/components/DashboardGreeting.vue'
import DashboardGreetingSkeleton from '@/app/features/dashboard/components/DashboardGreetingSkeleton.vue'
import PreApprovedProductsCard from '@/app/features/dashboard/components/PreApprovedProductsCard.vue'
import { useCompanyOverview } from '@/app/composables/useCompanyOverview'
import { useCompanyProducts } from '@/app/composables/useCompanyProducts'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFeatureFlags } from '@/app/composables/useFeatureFlags'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { isK1Enabled } = useFeatureFlags()

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

watch(() => props.inn, reloadDemoPersona, { immediate: true })
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
      @retry="reloadDemoPersona"
    />

    <DashboardGreetingSkeleton v-else />

    <!-- Финансовые карточки: количество и содержимое определяет бэкенд -->
    <DashboardSummarySection :inn="inn" />

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
