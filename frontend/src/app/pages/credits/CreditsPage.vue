<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
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

const { products: preApprovedProducts } = useCompanyProducts(() => props.inn)

const { profile, isProfileLoading } = useCompanyProfile(() => props.inn)
const {
  creditScore,
  isLoading: isScoreLoading,
  error: scoreError,
  isUnavailable: isScoreUnavailable,
  loadCreditScore,
} = useCreditScore(() => props.inn)

const HIGHLIGHT_MS = 1600

// Расчёт платежа раскрыт внутри одного варианта; сумма и срок оттуда уходят в заявку
const calculatorCode = ref<Nullable<CreditProductCodeEnum>>(null)
const calculatorTerms = ref<{ amount: Nullable<number>; termMonths: Nullable<number> }>({ amount: null, termMonths: null })
// Вариант, который выбрал бы банк, — подсвечиваем по «Пусть банк подберёт»
const highlightedCode = ref<Nullable<CreditProductCodeEnum>>(null)
let highlightTimer: ReturnType<typeof setTimeout> | undefined

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
const isBlocked = computed(() => blockers.value.length > 0)
// Без кредитной истории суммы и ставки предварительные: говорим это один раз над списком
const isPreliminary = computed(() => offers.value?.isBkiKnown === false)

// «Пусть банк подберёт» возможно, когда задача выбрана и компании что-то можно предложить
const isBankChoiceVisible = computed(() => Boolean(goal.value) && !isBlocked.value && availableOptions.value.length > 0)

// Почему банк выбрал бы этот вариант: закрывает всю сумму или даёт больше остальных
const recommendedReason = computed(() => {
  const featured = featuredOption.value

  if (!featured?.isRecommended || !amount.value || featured.amount === null) return ''

  return featured.amount >= amount.value ? t('credits.options.recommendedFull') : t('credits.options.recommendedMost')
})

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

function handleGoalChange(value: Nullable<CreditGoalEnum>) {
  goal.value = value
}

function handleAmountChange(value: Nullable<number>) {
  amount.value = value
}

function handleTermChange(value: Nullable<number>) {
  termMonths.value = value
}

// Заявка по варианту: его продукт, сумма и срок (или подобранные в расчёте), задача и личная ставка
function handleSelect(option: CompanyOfferOptionInterface) {
  const terms = calculatorCode.value === option.code ? calculatorTerms.value : { amount: null, termMonths: null }
  const optionAmount = terms.amount ?? option.amount ?? amount.value ?? option.maxAmount

  router.push({
    name: 'application-new',
    params: { inn: props.inn },
    query: {
      product: option.code,
      amount: optionAmount ?? undefined,
      term: terms.termMonths ?? option.termMonths ?? termMonths.value ?? undefined,
      goal: goal.value ?? undefined,
      // Ставка варианта: в форме — та же, а не «от» из каталога
      rate: option.rate ?? undefined,
      // Сколько показал вариант: если банк даст меньше, «Почему» скажет, откуда разница
      shown: option.amount ?? option.maxAmount ?? undefined,
      // Хотели больше, чем даёт вариант: форма скажет об этом и предложит подать на всю сумму
      ...(amount.value && optionAmount && amount.value > optionAmount ? { wanted: amount.value } : {}),
    },
  })
}

// «Пусть банк подберёт»: показываем, какой вариант выбрал бы банк
async function handleBankChoice() {
  const featured = featuredOption.value

  if (!featured) return

  clearTimeout(highlightTimer)
  highlightedCode.value = featured.code
  highlightTimer = setTimeout(clearHighlight, HIGHLIGHT_MS)

  await nextTick()

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  document.getElementById(`credit-option-${featured.code}`)
    ?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'center' })
}

function clearHighlight() {
  highlightedCode.value = null
}

function handleToggleCalculator(option: CompanyOfferOptionInterface) {
  calculatorCode.value = calculatorCode.value === option.code ? null : option.code
  calculatorTerms.value = { amount: null, termMonths: null }
}

function handleCalculatorChange(calcAmount: Nullable<number>, calcTermMonths: Nullable<number>) {
  calculatorTerms.value = { amount: calcAmount, termMonths: calcTermMonths }
}

function onInnChange() {
  calculatorCode.value = null
  goal.value = readGoalFromQuery()
  amount.value = null
  termMonths.value = null
}

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
        <!-- На что нужны деньги; при стоп-факторе выбирать не из чего -->
        <CreditGoalPicker
          v-if="!isBlocked"
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

          <!-- Стоп для всей компании: причина и действие вместо списка «не подходит» и калькулятора -->
          <div
            v-else-if="isBlocked"
            class="flex flex-col gap-4 rounded-3xl border border-red-500/30 bg-red-500/5 p-5 sm:p-6"
          >
            <div class="flex items-start gap-3">
              <span
                class="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-red-500/10 text-red-700
                       dark:text-red-400"
                aria-hidden="true"
              >
                <i class="pi pi-ban" />
              </span>

              <div class="min-w-0">
                <h2 class="text-lg font-bold tracking-tight text-fino-text">
                  {{ t('credits.options.blocked') }}
                </h2>

                <ul class="mt-1 flex flex-col gap-1 text-sm text-fino-text">
                  <li
                    v-for="blocker in blockers"
                    :key="blocker.code"
                    class="break-words"
                  >
                    {{ blocker.text }}
                  </li>
                </ul>

                <p class="mt-2 text-sm text-fino-text-muted">
                  {{ t('credits.options.blockedHint') }}
                </p>
              </div>
            </div>

            <button
              type="button"
              class="inline-flex min-h-11 w-fit cursor-pointer items-center gap-2 rounded-xl bg-primary px-5 text-sm
                     font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90 active:scale-95
                     disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              :disabled="isOffersLoading"
              @click="loadOffers"
            >
              <i
                :class="isOffersLoading ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'"
                class="text-xs"
                aria-hidden="true"
              />
              {{ t('credits.options.checkAgain') }}
            </button>
          </div>

          <template v-else-if="offers">
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

            <!-- Без кредитной истории — одна строка над списком, а не плашка на каждой карточке -->
            <p
              v-if="isPreliminary"
              class="flex items-start gap-2 rounded-2xl bg-amber-500/10 px-4 py-3 text-sm text-fino-text"
            >
              <i
                class="pi pi-info-circle mt-0.5 text-amber-700 dark:text-amber-400"
                aria-hidden="true"
              />
              <span class="min-w-0">{{ t('credits.options.preliminary') }}</span>
            </p>

            <div
              v-if="featuredOption"
              :id="`credit-option-${featuredOption.code}`"
              class="scroll-mt-28"
            >
              <p
                v-if="recommendedReason"
                class="mb-2 text-xs font-semibold text-fino-text-muted"
              >
                {{ recommendedReason }}
              </p>

              <CreditOptionCard
                :option="featuredOption"
                is-featured
                :is-preliminary="isPreliminary"
                :is-calculator-open="calculatorCode === featuredOption.code"
                :is-highlighted="highlightedCode === featuredOption.code"
                @select="handleSelect"
                @toggle-calculator="handleToggleCalculator"
              >
                <template #calculator>
                  <LoanCalculator
                    :inn="inn"
                    :products="catalogProducts"
                    :pre-approved-products="preApprovedProducts"
                    :selected-code="featuredOption.code"
                    :context="calcContext"
                    :is-products-loading="isCatalogLoading"
                    is-embedded
                    :initial-amount="featuredOption.amount ?? featuredOption.maxAmount"
                    :initial-term-months="featuredOption.termMonths"
                    @change="handleCalculatorChange"
                  />
                </template>
              </CreditOptionCard>
            </div>

            <p
              v-else
              class="rounded-3xl border border-dashed border-fino-border bg-fino-surface p-6 text-sm text-fino-text-muted"
            >
              {{ t('credits.options.none') }}
            </p>

            <TransitionGroup
              v-if="otherOptions.length"
              tag="ul"
              class="grid grid-cols-1 items-start gap-4 md:grid-cols-2"
              move-class="transition-transform duration-300 ease-out motion-reduce:transition-none"
              enter-active-class="transition duration-200 motion-reduce:transition-none"
              enter-from-class="opacity-0"
            >
              <li
                v-for="option in otherOptions"
                :key="option.code"
                :class="{ 'md:col-span-2': calculatorCode === option.code }"
              >
                <CreditOptionCard
                  :option="option"
                  :is-featured="false"
                  :is-preliminary="isPreliminary"
                  :is-calculator-open="calculatorCode === option.code"
                  @select="handleSelect"
                  @toggle-calculator="handleToggleCalculator"
                >
                  <template #calculator>
                    <LoanCalculator
                      :inn="inn"
                      :products="catalogProducts"
                      :pre-approved-products="preApprovedProducts"
                      :selected-code="option.code"
                      :context="calcContext"
                      :is-products-loading="isCatalogLoading"
                      is-embedded
                      :initial-amount="option.amount ?? option.maxAmount"
                      :initial-term-months="option.termMonths"
                      @change="handleCalculatorChange"
                    />
                  </template>
                </CreditOptionCard>
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
