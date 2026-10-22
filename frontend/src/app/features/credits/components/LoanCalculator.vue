<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import AppErrorState from '@/app/components/AppErrorState.vue'
import LoanCalculatorSkeleton from './LoanCalculatorSkeleton.vue'
import LoanSchedule from './LoanSchedule.vue'
import RepaymentComparison from './RepaymentComparison.vue'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { useLoanCalculator } from '@/app/composables/useLoanCalculator'
import { useRepayment } from '@/app/composables/useRepayment'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { CatalogProductInterface } from '@/app/types/catalog/catalog-product-interface'
import type { LoanCalcContextInterface, LoanCalcParamsInterface } from '@/app/types/catalog/loan-calc-interface'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  inn: string
  products: CatalogProductInterface[]
  preApprovedProducts: CreditProductInterface[]
  selectedCode: Nullable<CreditProductCodeEnum>
  context: Nullable<LoanCalcContextInterface>
  isProductsLoading: boolean
}>()

const emit = defineEmits<{
  selectProduct: [productCode: CreditProductCodeEnum]
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const form = reactive<{ amount: Nullable<number>, termMonths: Nullable<number> }>({
  amount: null,
  termMonths: null,
})

const selectedProduct = computed(() => props.products.find((product) => product.code === props.selectedCode) ?? null)

const productOptions = computed(() => props.products.map((product) => ({ code: product.code, name: product.name })))

const preApproved = computed(() => props.preApprovedProducts.find((product) => product.code === props.selectedCode) ?? null)

const isAmountValid = computed(() => {
  const product = selectedProduct.value

  return Boolean(product && form.amount !== null && form.amount >= product.amountMin && form.amount <= product.amountMax)
})

const isTermValid = computed(() => {
  const product = selectedProduct.value

  return Boolean(
    product && form.termMonths !== null
    && form.termMonths >= product.termMonthsMin && form.termMonths <= product.termMonthsMax,
  )
})

const isTermFixed = computed(() => selectedProduct.value?.termMonthsMin === selectedProduct.value?.termMonthsMax)

const amountHint = computed(() =>
  selectedProduct.value
    ? t('credits.products.amountRange', {
      min: formatCurrency(selectedProduct.value.amountMin, 'RUB'),
      max: formatCurrency(selectedProduct.value.amountMax, 'RUB'),
    })
    : undefined,
)

const termHint = computed(() =>
  selectedProduct.value && !isTermFixed.value
    ? t('credits.products.termRange', {
      min: selectedProduct.value.termMonthsMin,
      max: selectedProduct.value.termMonthsMax,
    })
    : undefined,
)

const termSuffix = computed(() => ` ${t('credits.calculator.months')}`)

// Считаем только по корректной форме и когда известны данные компании: от них зависит ставка
const params = computed<Nullable<LoanCalcParamsInterface>>(() => {
  const product = selectedProduct.value

  if (!product || !props.context || !isAmountValid.value || !isTermValid.value) return null

  return {
    ...props.context,
    product: product.code,
    amount: form.amount as number,
    termMonths: form.termMonths as number,
  }
})

const { result, isLoading, error, calculate } = useLoanCalculator(params)

// Способ погашения сравниваем по тем же сумме и сроку, но по ставке из расчёта
const repaymentParams = computed(() =>
  params.value && result.value && !isLoading.value
    ? { amount: params.value.amount, termMonths: params.value.termMonths, rate: result.value.rate }
    : null,
)

const {
  repayment,
  isLoading: isRepaymentLoading,
  error: repaymentError,
  isUnavailable: isRepaymentUnavailable,
  loadRepayment,
} = useRepayment(() => props.inn, repaymentParams)

const isInvalid = computed(() => Boolean(selectedProduct.value && !params.value && props.context))
const isSkeletonVisible = computed(() => (isLoading.value && !result.value) || !props.context)

const rateParts = computed(() => {
  const current = result.value

  if (!current || current.keyRate === null) return ''

  return t('credits.calculator.rateParts', {
    key: formatPercent(current.keyRate),
    industry: formatPercent(current.industrySpread ?? 0),
    risk: formatPercent(current.riskSpread ?? 0),
  })
})

const applyRoute = computed(() => ({
  name: 'application-new',
  params: { inn: props.inn },
  query: {
    product: selectedProduct.value?.code,
    amount: form.amount ?? undefined,
    term: form.termMonths ?? undefined,
  },
}))

// При выборе продукта подставляем предодобренные условия, иначе — минимум продукта
function applyProductDefaults() {
  const product = selectedProduct.value

  if (!product) return

  form.amount = preApproved.value
    ? Math.min(Math.max(preApproved.value.amount, product.amountMin), product.amountMax)
    : product.amountMin
  form.termMonths = preApproved.value
    ? Math.min(Math.max(preApproved.value.termMonths, product.termMonthsMin), product.termMonthsMax)
    : product.termMonthsMin
}

function handleProductChange(productCode: CreditProductCodeEnum) {
  emit('selectProduct', productCode)
}

// Условия подставляем при выборе продукта (и когда каталог догрузился); позднее предодобрение введённое не затирает
watch(() => selectedProduct.value?.code, applyProductDefaults, { immediate: true })
</script>

<template>
  <section class="flex flex-col gap-6">
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('credits.calculator.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('credits.calculator.description') }}
      </p>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <SandboxPersonaField
        class="sm:col-span-2 xl:col-span-1"
        input-id="calc-product"
        :label="t('credits.calculator.product')"
        :error="null"
      >
        <Select
          :model-value="selectedCode"
          input-id="calc-product"
          :options="productOptions"
          option-label="name"
          option-value="code"
          :placeholder="t('credits.calculator.productPlaceholder')"
          :loading="isProductsLoading"
          fluid
          @update:model-value="handleProductChange"
        />
      </SandboxPersonaField>

      <SandboxPersonaField
        input-id="calc-amount"
        :label="t('credits.calculator.amount')"
        :hint="amountHint"
        :error="null"
      >
        <InputNumber
          v-model="form.amount"
          input-id="calc-amount"
          :min="selectedProduct?.amountMin"
          :max="selectedProduct?.amountMax"
          :max-fraction-digits="0"
          suffix=" ₽"
          :locale="locale"
          :disabled="!selectedProduct"
          :invalid="Boolean(selectedProduct) && form.amount !== null && !isAmountValid"
          fluid
        />
      </SandboxPersonaField>

      <SandboxPersonaField
        input-id="calc-term"
        :label="t('credits.calculator.term')"
        :hint="termHint"
        :error="null"
      >
        <InputNumber
          v-model="form.termMonths"
          input-id="calc-term"
          :min="selectedProduct?.termMonthsMin"
          :max="selectedProduct?.termMonthsMax"
          :max-fraction-digits="0"
          :suffix="termSuffix"
          :locale="locale"
          :disabled="!selectedProduct || isTermFixed"
          :invalid="Boolean(selectedProduct) && form.termMonths !== null && !isTermValid"
          fluid
        />
      </SandboxPersonaField>
    </div>

    <div
      class="flex flex-col gap-6"
      aria-live="polite"
    >
      <p
        v-if="!selectedProduct"
        class="rounded-2xl bg-fino-surface-secondary p-4 text-sm text-fino-text-muted"
      >
        {{ t('credits.calculator.choose') }}
      </p>

      <LoanCalculatorSkeleton v-else-if="isSkeletonVisible && !isInvalid" />

      <p
        v-else-if="isInvalid"
        class="rounded-2xl bg-fino-accent p-4 text-sm text-fino-text"
      >
        {{ t('credits.calculator.invalid') }}
      </p>

      <AppErrorState
        v-else-if="error"
        :message="t('credits.calculator.error')"
        is-inline
        @retry="calculate"
      />

      <template v-else-if="result">
        <dl class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div class="rounded-2xl bg-fino-accent p-4">
            <dt class="text-xs text-fino-text-muted">
              {{ t('credits.calculator.rate') }}
            </dt>
            <dd class="mt-1 text-3xl font-bold tracking-tight text-primary">
              {{ formatPercent(result.rate) }}
            </dd>
            <dd
              v-if="rateParts"
              class="mt-1 break-words text-xs text-fino-text-muted"
            >
              {{ rateParts }}
            </dd>
          </div>

          <div class="rounded-2xl bg-fino-surface-secondary p-4">
            <dt class="text-xs text-fino-text-muted">
              {{ t('credits.calculator.payment') }}
            </dt>
            <dd class="mt-1 break-words text-2xl font-bold tracking-tight text-fino-text">
              {{ formatCurrency(result.payment, 'RUB') }}
            </dd>
            <dd class="mt-1 text-xs text-fino-text-muted">
              {{ t(`credits.calculator.repaymentHint.${result.repayment}`) }}
            </dd>
          </div>

          <div class="rounded-2xl bg-fino-surface-secondary p-4">
            <dt class="text-xs text-fino-text-muted">
              {{ t('credits.calculator.overpayment') }}
            </dt>
            <dd class="mt-1 break-words text-2xl font-bold tracking-tight text-fino-text">
              {{ formatCurrency(result.overpayment, 'RUB') }}
            </dd>
            <dd class="mt-1 text-xs text-fino-text-muted">
              {{ t('credits.calculator.overpaymentHint') }}
            </dd>
          </div>
        </dl>

        <div
          v-if="result.schedule.length"
          class="rounded-2xl border border-fino-border p-4"
        >
          <h3 class="mb-2 text-sm font-semibold text-fino-text">
            {{ t('credits.schedule.title') }}
          </h3>

          <LoanSchedule :schedule="result.schedule" />
        </div>

        <RepaymentComparison
          v-if="!isRepaymentUnavailable"
          :repayment="repayment"
          :is-loading="isRepaymentLoading || isLoading"
          :has-error="repaymentError"
          @retry="loadRepayment"
        />

        <RouterLink
          :to="applyRoute"
          class="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3
                 text-sm font-semibold text-primary-contrast transition-all duration-200
                 hover:opacity-90 active:scale-95 motion-reduce:transition-none sm:w-fit
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {{ t('credits.calculator.apply') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </RouterLink>
      </template>
    </div>
  </section>
</template>
