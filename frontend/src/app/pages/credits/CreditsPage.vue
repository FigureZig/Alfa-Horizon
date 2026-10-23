<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import SelectButton from 'primevue/selectbutton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CreditHealthCard from '@/app/features/credits/components/CreditHealthCard.vue'
import CreditProductCard from '@/app/features/credits/components/CreditProductCard.vue'
import CreditProductCardSkeleton from '@/app/features/credits/components/CreditProductCardSkeleton.vue'
import LoanCalculator from '@/app/features/credits/components/LoanCalculator.vue'
import { useCatalogProducts } from '@/app/composables/useCatalogProducts'
import { useCompanyProducts } from '@/app/composables/useCompanyProducts'
import { useCompanyProfile } from '@/app/composables/useCompanyProfile'
import { useCreditScore } from '@/app/composables/useCreditScore'
import { useFormatters } from '@/app/composables/useFormatters'
import { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { LoanCalcContextInterface } from '@/app/types/catalog/loan-calc-interface'
import type { Nullable } from '@/app/types/nullable'

const PRODUCT_SKELETON_COUNT = 6
const ALL_GOALS = 'all'

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatPercent } = useFormatters()

const {
  products: catalogProducts,
  keyRate,
  isLoading: isCatalogLoading,
  error: catalogError,
  loadProducts: loadCatalog,
} = useCatalogProducts()

// Предодобрение (K2) — те же данные, что и на главной
const {
  products: preApprovedProducts,
  isProductsLoading: isPreApprovedLoading,
} = useCompanyProducts(() => props.inn)

const { profile, isProfileLoading } = useCompanyProfile(() => props.inn)
const {
  creditScore,
  isLoading: isScoreLoading,
  error: scoreError,
  isUnavailable: isScoreUnavailable,
  loadCreditScore,
} = useCreditScore(() => props.inn)

const calculatorRef = useTemplateRef<HTMLElement>('calculator')

const selectedCode = ref<Nullable<CreditProductCodeEnum>>(null)
// Цель может прийти из адреса: например, с главной по карточке госконтракта
const route = useRoute()
const goalFilter = ref<string>(typeof route.query.goal === 'string' ? route.query.goal : ALL_GOALS)

const isCatalogEmpty = computed(() => !isCatalogLoading.value && !catalogError.value && !catalogProducts.value.length)

// Ставка зависит от формы, отрасли и класса риска компании: считаем, когда они известны
const calcContext = computed<Nullable<LoanCalcContextInterface>>(() => {
  if (isProfileLoading.value || isScoreLoading.value) return null

  return {
    segment: profile.value?.legalForm ?? LegalFormEnum.SoleProprietor,
    section: profile.value?.section ?? null,
    riskClass: creditScore.value?.riskClass ?? RiskClassEnum.B,
  }
})

const goalOptions = computed(() => {
  const goals = [...new Set(catalogProducts.value.flatMap((product) => product.goals))]

  return [
    { code: ALL_GOALS, label: t('credits.products.goalAll') },
    ...goals.map((goal) => ({ code: goal, label: t(`application.goal.${goal}`) })),
  ]
})

const visibleProducts = computed(() =>
  goalFilter.value === ALL_GOALS
    ? catalogProducts.value
    : catalogProducts.value.filter((product) => product.goals.some((goal) => goal === goalFilter.value)),
)

const cards = computed(() =>
  visibleProducts.value.map((product) => ({
    product,
    preApproved: preApprovedProducts.value.find((item) => item.code === product.code) ?? null,
    isSelected: product.code === selectedCode.value,
  })),
)

const keyRateText = computed(() =>
  keyRate.value === null ? '' : t('credits.keyRate', { rate: formatPercent(keyRate.value) }),
)

// Калькулятор сразу показывает расчёт: берём предодобренный продукт, а если его нет — первый из каталога
function selectDefaultProduct() {
  if (selectedCode.value || !catalogProducts.value.length || isPreApprovedLoading.value) return

  selectedCode.value = preApprovedProducts.value[0]?.code ?? catalogProducts.value[0].code
}

function handleCalculate(productCode: CreditProductCodeEnum) {
  selectedCode.value = productCode

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  calculatorRef.value?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' })
}

function handleSelectProduct(productCode: CreditProductCodeEnum) {
  selectedCode.value = productCode
}

function onInnChange() {
  selectedCode.value = null
  goalFilter.value = ALL_GOALS
}

watch([catalogProducts, preApprovedProducts, isPreApprovedLoading], selectDefaultProduct, { immediate: true })
watch(() => props.inn, onInnChange)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('credits.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm text-fino-text-muted">
          {{ t('credits.description') }}
        </p>
      </div>

      <p
        v-if="keyRateText"
        class="inline-flex items-center gap-2 rounded-xl bg-fino-accent px-3 py-2 text-sm font-semibold text-primary"
      >
        <i
          class="pi pi-percentage text-xs"
          aria-hidden="true"
        />
        {{ keyRateText }}
      </p>
    </div>

    <div class="grid grid-cols-1 items-start gap-6 2xl:grid-cols-[minmax(0,1fr)_24rem]">
      <div class="flex min-w-0 flex-col gap-6">
        <!-- Продукты банка -->
        <section
          class="flex flex-col gap-4"
          :aria-label="t('credits.products.title')"
        >
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h2 class="text-lg font-bold tracking-tight text-fino-text">
              {{ t('credits.products.title') }}
            </h2>

            <!-- Прокручивается внутри контейнера, подписи целей не переносятся -->
            <div
              v-if="goalOptions.length > 2"
              class="-mx-1 max-w-full overflow-x-auto px-1 py-1"
            >
              <SelectButton
                v-model="goalFilter"
                :options="goalOptions"
                option-label="label"
                option-value="code"
                :allow-empty="false"
                :aria-label="t('credits.products.goal')"
                class="w-max [&_button]:whitespace-nowrap"
              />
            </div>
          </div>

          <div
            v-if="isCatalogLoading && !catalogProducts.length"
            class="grid grid-cols-1 gap-4 md:grid-cols-2"
            aria-busy="true"
          >
            <CreditProductCardSkeleton
              v-for="index in PRODUCT_SKELETON_COUNT"
              :key="index"
            />
          </div>

          <AppErrorState
            v-else-if="catalogError"
            :message="t('credits.products.loadError')"
            @retry="loadCatalog"
          />

          <p
            v-else-if="isCatalogEmpty"
            class="rounded-3xl border border-dashed border-fino-border bg-fino-surface p-6 text-sm text-fino-text-muted"
          >
            {{ t('credits.products.empty') }}
          </p>

          <ul
            v-else
            class="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            <li
              v-for="card in cards"
              :key="card.product.code"
              class="flex"
            >
              <CreditProductCard
                class="w-full"
                :product="card.product"
                :inn="inn"
                :pre-approved="card.preApproved"
                :is-selected="card.isSelected"
                @calculate="handleCalculate"
              />
            </li>
          </ul>
        </section>

        <!-- Калькулятор: расчёт и способ погашения -->
        <div
          ref="calculator"
          class="scroll-mt-28 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6"
        >
          <LoanCalculator
            :inn="inn"
            :products="catalogProducts"
            :pre-approved-products="preApprovedProducts"
            :selected-code="selectedCode"
            :context="calcContext"
            :is-products-loading="isCatalogLoading"
            @select-product="handleSelectProduct"
          />
        </div>
      </div>

      <!-- Кредитное здоровье -->
      <aside
        v-if="!isScoreUnavailable"
        class="min-w-0 2xl:sticky 2xl:top-28"
      >
        <CreditHealthCard
          :credit-score="creditScore"
          :is-loading="isScoreLoading"
          :has-error="scoreError"
          @retry="loadCreditScore"
        />
      </aside>
    </div>
  </div>
</template>
