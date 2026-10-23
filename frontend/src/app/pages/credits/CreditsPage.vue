<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CreditGoalPicker from '@/app/features/credits/components/CreditGoalPicker.vue'
import CreditHealthCard from '@/app/features/credits/components/CreditHealthCard.vue'
import CreditOptionCard from '@/app/features/credits/components/CreditOptionCard.vue'
import CreditOptionsSkeleton from '@/app/features/credits/components/CreditOptionsSkeleton.vue'
import LoanCalculator from '@/app/features/credits/components/LoanCalculator.vue'
import { useCatalogProducts } from '@/app/composables/useCatalogProducts'
import { useCompanyOffers } from '@/app/composables/useCompanyOffers'
import { useCompanyProducts } from '@/app/composables/useCompanyProducts'
import { useCompanyProfile } from '@/app/composables/useCompanyProfile'
import { useCreditScore } from '@/app/composables/useCreditScore'
import { useFormatters } from '@/app/composables/useFormatters'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { LoanCalcContextInterface } from '@/app/types/catalog/loan-calc-interface'
import type { CompanyOfferOptionInterface } from '@/app/types/company/company-offers-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const { formatPercent } = useFormatters()

// Продукты каталога и предодобрение нужны калькулятору: он считает ставку по продукту и классу риска
const {
  products: catalogProducts,
  keyRate,
  isLoading: isCatalogLoading,
} = useCatalogProducts()

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

// Задача может прийти из адреса: например, с карточки госконтракта на главной
function readGoalFromQuery(): Nullable<CreditGoalEnum> {
  return Object.values(CreditGoalEnum).find((goal) => goal === route.query.goal) ?? null
}

const goal = ref<Nullable<CreditGoalEnum>>(readGoalFromQuery())
const amount = ref<Nullable<number>>(null)
const termMonths = ref<Nullable<number>>(null)

const offersParams = computed(() => ({ goal: goal.value, amount: amount.value, termMonths: termMonths.value }))
const { offers, isLoading: isOffersLoading, error: offersError, loadOffers } = useCompanyOffers(
  () => props.inn,
  offersParams,
)

const isOffersSkeletonVisible = computed(() => isOffersLoading.value && !offers.value)

// Рекомендованный — крупно, остальные доступные — ниже, недоступные — свёрнуто с причиной
const availableOptions = computed(() => (offers.value?.options ?? []).filter((option) => option.isAvailable))
const featuredOption = computed(() => availableOptions.value.find((option) => option.isRecommended) ?? availableOptions.value[0] ?? null)
const otherOptions = computed(() => availableOptions.value.filter((option) => option !== featuredOption.value))
const unavailableOptions = computed(() => (offers.value?.options ?? []).filter((option) => !option.isAvailable))
const blockers = computed(() => offers.value?.blockers ?? [])

// «Пусть банк подберёт» возможно, когда задача выбрана и компании что-то можно предложить
const isBankChoiceVisible = computed(() => Boolean(goal.value) && !blockers.value.length && availableOptions.value.length > 0)

// Ставка зависит от формы, отрасли и класса риска компании: считаем, когда они известны
const calcContext = computed<Nullable<LoanCalcContextInterface>>(() => {
  if (isProfileLoading.value || isScoreLoading.value) return null

  return {
    segment: profile.value?.legalForm ?? LegalFormEnum.SoleProprietor,
    section: profile.value?.section ?? null,
    riskClass: creditScore.value?.riskClass ?? RiskClassEnum.B,
  }
})

const keyRateText = computed(() =>
  keyRate.value === null ? '' : t('credits.keyRate', { rate: formatPercent(keyRate.value) }),
)

// Калькулятор сразу показывает расчёт: берём предодобренный продукт, а если его нет — первый из каталога
function selectDefaultProduct() {
  if (selectedCode.value || !catalogProducts.value.length || isPreApprovedLoading.value) return

  selectedCode.value = preApprovedProducts.value[0]?.code ?? catalogProducts.value[0].code
}

function handleGoalChange(value: Nullable<CreditGoalEnum>) {
  goal.value = value
}

function handleAmountChange(value: Nullable<number>) {
  amount.value = value
}

function handleTermChange(value: Nullable<number>) {
  termMonths.value = value
}

// Заявка по варианту: открывается с его продуктом, суммой, сроком и задачей
function handleApply(option: CompanyOfferOptionInterface) {
  router.push({
    name: 'application-new',
    params: { inn: props.inn },
    query: {
      product: option.code,
      amount: option.amount ?? amount.value ?? option.maxAmount ?? undefined,
      term: option.termMonths ?? termMonths.value ?? undefined,
      goal: goal.value ?? undefined,
      // Сколько показал вариант: если банк даст меньше, «Почему» скажет, откуда разница
      shown: option.amount ?? option.maxAmount ?? undefined,
    },
  })
}

// Без продукта: банк подберёт сам по задаче
function handleBankChoice() {
  router.push({
    name: 'application-new',
    params: { inn: props.inn },
    query: { goal: goal.value ?? undefined, amount: amount.value ?? undefined, term: termMonths.value ?? undefined },
  })
}

function handleCalculate(option: CompanyOfferOptionInterface) {
  selectedCode.value = option.code

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  calculatorRef.value?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' })
}

function handleSelectProduct(productCode: CreditProductCodeEnum) {
  selectedCode.value = productCode
}

function onInnChange() {
  selectedCode.value = null
  goal.value = readGoalFromQuery()
  amount.value = null
  termMonths.value = null
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
        <!-- На что нужны деньги -->
        <CreditGoalPicker
          :goal="goal"
          :amount="amount"
          :term-months="termMonths"
          @update:goal="handleGoalChange"
          @update:amount="handleAmountChange"
          @update:term-months="handleTermChange"
        />

        <!-- Что банк предложит именно вам -->
        <section
          class="flex flex-col gap-4"
          :aria-label="t('credits.options.title')"
          :aria-busy="isOffersLoading"
        >
          <CreditOptionsSkeleton v-if="isOffersSkeletonVisible" />

          <AppErrorState
            v-else-if="offersError"
            :message="t('credits.options.loadError')"
            @retry="loadOffers"
          />

          <template v-else-if="offers">
            <!-- Стоп для всей компании: причина и что делать -->
            <div
              v-if="blockers.length"
              class="rounded-3xl border border-red-500/30 bg-red-500/5 p-5"
            >
              <p class="flex items-center gap-2 text-sm font-bold text-red-700 dark:text-red-400">
                <i
                  class="pi pi-ban"
                  aria-hidden="true"
                />
                {{ t('credits.options.blocked') }}
              </p>

              <ul class="mt-2 flex flex-col gap-1.5 text-sm text-fino-text">
                <li
                  v-for="blocker in blockers"
                  :key="blocker.code"
                >
                  {{ blocker.text }}
                </li>
              </ul>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3">
              <h2 class="text-lg font-bold tracking-tight text-fino-text">
                {{ t('credits.options.title') }}
              </h2>

              <button
                v-if="isBankChoiceVisible"
                type="button"
                class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-xl border border-fino-border
                       bg-fino-surface px-4 text-sm font-semibold text-fino-text transition-colors duration-200
                       hover:border-primary hover:text-primary focus-visible:outline-2 focus-visible:outline-primary
                       motion-reduce:transition-none"
                @click="handleBankChoice"
              >
                <i
                  class="pi pi-sparkles text-xs"
                  aria-hidden="true"
                />
                {{ t('credits.options.bankChoice') }}
              </button>
            </div>

            <CreditOptionCard
              v-if="featuredOption"
              :option="featuredOption"
              is-featured
              @apply="handleApply"
              @calculate="handleCalculate"
            />

            <p
              v-else-if="!blockers.length"
              class="rounded-3xl border border-dashed border-fino-border bg-fino-surface p-6 text-sm text-fino-text-muted"
            >
              {{ t('credits.options.none') }}
            </p>

            <TransitionGroup
              v-if="otherOptions.length"
              tag="ul"
              class="grid grid-cols-1 gap-4 md:grid-cols-2"
              move-class="transition-transform duration-300 ease-out motion-reduce:transition-none"
              enter-active-class="transition duration-200 motion-reduce:transition-none"
              enter-from-class="opacity-0"
            >
              <li
                v-for="option in otherOptions"
                :key="option.code"
              >
                <CreditOptionCard
                  :option="option"
                  :is-featured="false"
                  @apply="handleApply"
                  @calculate="handleCalculate"
                />
              </li>
            </TransitionGroup>

            <!-- Не подходит компании: свёрнуто, с причиной -->
            <details
              v-if="unavailableOptions.length"
              class="group rounded-2xl border border-fino-border bg-fino-surface"
            >
              <summary
                class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                       text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
              >
                {{ t('credits.options.unavailable', unavailableOptions.length) }}
                <i
                  class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                         group-open:rotate-180 motion-reduce:transition-none"
                  aria-hidden="true"
                />
              </summary>

              <ul class="flex flex-col divide-y divide-fino-border px-4 pb-2">
                <li
                  v-for="option in unavailableOptions"
                  :key="option.code"
                  class="py-3"
                >
                  <p class="text-sm font-semibold text-fino-text">
                    {{ option.name }}
                  </p>

                  <p class="mt-0.5 text-xs leading-relaxed text-fino-text-muted">
                    {{ option.reasons.join(' ') }}
                  </p>
                </li>
              </ul>
            </details>
          </template>
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
