<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import AppErrorState from '@/app/components/AppErrorState.vue'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import { useApplicationCreate } from '@/app/composables/useApplicationCreate'
import { useCatalogProducts } from '@/app/composables/useCatalogProducts'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationProductChoiceEnum } from '@/app/types/application/application-product-choice-enum'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { ApplicationFormInterface } from '@/app/types/application/application-form-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  inn: string
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const { formatCurrency, formatMoney, formatPercent } = useFormatters()
const { demoPersona } = useDemoPersona()
const { products, isLoading: isCatalogLoading, error: catalogError, loadProducts } = useCatalogProducts()
const { isSubmitting, errorMessage, createAndSubmit } = useApplicationCreate(props.inn)

const form = reactive<ApplicationFormInterface>({
  product: null,
  amount: null,
  termMonths: null,
  goal: null,
  consentBki: false,
})

const isSubmitted = ref(false)
const isPrefilled = ref(false)

const selectedProduct = computed(() => products.value.find((product) => product.code === form.product) ?? null)

// Продукт можно не выбирать: «Пусть банк подберёт» — тогда нужна задача, а продукт банк определит сам
const isBankChoice = computed(() => form.product === ApplicationProductChoiceEnum.BankChoice)

const productOptions = computed(() => [
  { code: ApplicationProductChoiceEnum.BankChoice, name: t('application.new.bankChoice') },
  ...products.value.map((product) => ({ code: product.code, name: product.name })),
])

const goalOptions = computed(() => {
  const goals = isBankChoice.value ? Object.values(CreditGoalEnum) : selectedProduct.value?.goals ?? []

  return goals.map((goal) => ({ code: goal, label: t(`application.goal.${goal}`) }))
})

type FormErrorKey = 'product' | 'amount' | 'termMonths' | 'goal'

// Пока продукт не выбран, поля заблокированы: подсказка объясняет почему
const amountHint = computed(() =>
  isBankChoice.value
    ? t('application.new.bankChoiceHint')
    : selectedProduct.value
    ? t('application.new.amountRange', {
      min: formatCurrency(selectedProduct.value.amountMin, 'RUB'),
      max: formatCurrency(selectedProduct.value.amountMax, 'RUB'),
    })
    : t('application.new.selectProductFirst'),
)

// Фиксированный срок — просто «12 мес.», а не «от 12 до 12»
const termHint = computed(() => {
  if (isBankChoice.value) return undefined

  const product = selectedProduct.value

  if (!product) return t('application.new.selectProductFirst')

  return product.termMonthsMin === product.termMonthsMax
    ? t('credits.products.termFixed', { months: product.termMonthsMin })
    : t('application.new.termRange', { min: product.termMonthsMin, max: product.termMonthsMax })
})

const termSuffix = computed(() => ` ${t('application.new.months')}`)

const errors = computed<Partial<Record<FormErrorKey, string>>>(() => {
  if (!isSubmitted.value) return {}

  const product = selectedProduct.value
  const required = t('application.new.required')
  const result: Partial<Record<FormErrorKey, string>> = {}

  if (!form.product) {
    result.product = required
    return result
  }

  // Без продукта банк подбирает его по задаче: границ продукта нет, но нужны задача и сумма
  if (isBankChoice.value) {
    if (!form.goal) result.goal = t('application.errors.goalRequired')
    if (form.amount === null) result.amount = required

    return result
  }

  if (!product) return result

  if (form.amount === null) {
    result.amount = required
  } else if (form.amount < product.amountMin || form.amount > product.amountMax) {
    result.amount = t('application.new.amountRange', {
      min: formatCurrency(product.amountMin, 'RUB'),
      max: formatCurrency(product.amountMax, 'RUB'),
    })
  }

  if (form.termMonths === null) {
    result.termMonths = required
  } else if (form.termMonths < product.termMonthsMin || form.termMonths > product.termMonthsMax) {
    result.termMonths = t('application.new.termRange', { min: product.termMonthsMin, max: product.termMonthsMax })
  }

  return result
})

const isFormValid = computed(() => {
  const product = selectedProduct.value

  if (isBankChoice.value) return Boolean(form.goal && form.amount !== null && form.amount > 0)

  return Boolean(
    product
    && form.amount !== null && form.amount >= product.amountMin && form.amount <= product.amountMax
    && form.termMonths !== null && form.termMonths >= product.termMonthsMin && form.termMonths <= product.termMonthsMax,
  )
})

function parseNumberQuery(value: unknown): Nullable<number> {
  const parsed = typeof value === 'string' ? Number(value) : NaN

  return Number.isFinite(parsed) ? parsed : null
}

// Личная ставка варианта из подбора: в сводке — она, а не «от» из каталога
const offerRate = computed(() => parseNumberQuery(route.query.rate))
const rateText = computed(() => (offerRate.value === null ? '' : t('application.new.rate', { rate: formatPercent(offerRate.value) })))

// Хотели больше, чем банк готов дать по варианту: не подменяем сумму молча, а говорим и даём выбор
const wantedAmount = computed(() => parseNumberQuery(route.query.wanted))
const isWantedNoticeVisible = computed(() =>
  Boolean(wantedAmount.value && form.amount !== null && form.amount < wantedAmount.value && !isBankChoice.value),
)
const wantedNotice = computed(() =>
  wantedAmount.value && form.amount !== null
    ? t('application.new.wanted.text', { wanted: formatMoney(wantedAmount.value), amount: formatMoney(form.amount) })
    : '',
)

function applyWantedAmount() {
  const product = selectedProduct.value

  if (!wantedAmount.value) return

  form.amount = product ? Math.min(wantedAmount.value, product.amountMax) : wantedAmount.value
}

// Подставляем в форму предложение, с которого пришёл пользователь: продукт, сумму, срок и цель из адреса
function applyQueryPrefill() {
  const product = products.value.find((item) => item.code === route.query.product)

  // Пришли с задачей, но без продукта (например, «Пусть банк подберёт»)
  if (!product) {
    const goal = Object.values(CreditGoalEnum).find((item) => item === route.query.goal)

    if (goal) {
      form.product = ApplicationProductChoiceEnum.BankChoice
      form.goal = goal
      form.amount = parseNumberQuery(route.query.amount)
      form.termMonths = parseNumberQuery(route.query.term)
    }

    return
  }

  form.product = product.code
  form.amount = parseNumberQuery(route.query.amount) ?? product.amountMin
  form.termMonths = parseNumberQuery(route.query.term) ?? product.termMonthsMin
  form.goal = product.goals.find((goal) => goal === route.query.goal) ?? null
}

// Сумма, срок и цель должны подходить выбранному продукту
function applyProductBounds() {
  const product = selectedProduct.value

  if (!product) return

  form.amount = form.amount === null
    ? product.amountMin
    : Math.min(Math.max(form.amount, product.amountMin), product.amountMax)
  form.termMonths = form.termMonths === null
    ? product.termMonthsMin
    : Math.min(Math.max(form.termMonths, product.termMonthsMin), product.termMonthsMax)

  if (form.goal && !product.goals.includes(form.goal)) {
    form.goal = null
  }
}

async function handleSubmit() {
  isSubmitted.value = true

  if (!isFormValid.value) return

  const application = await createAndSubmit(form)

  if (application) {
    await router.push({
      name: 'application',
      params: { inn: props.inn, applicationId: application.id },
      query: {
        ...(route.query.guide === props.inn ? { guide: props.inn } : {}),
        // Сколько показывал подбор — страница заявки сравнит с решением
        ...(typeof route.query.shown === 'string' ? { shown: route.query.shown } : {}),
      },
    })
  }
}

function handleCancel() {
  router.push({ name: 'applications', params: { inn: props.inn } })
}

function handleCatalogLoaded() {
  if (isPrefilled.value || !products.value.length) return

  isPrefilled.value = true
  applyQueryPrefill()
}

watch(products, handleCatalogLoaded, { immediate: true })
watch(() => form.product, applyProductBounds)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div>
      <RouterLink
        :to="{ name: 'applications', params: { inn } }"
        class="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        <i
          class="pi pi-arrow-left text-xs"
          aria-hidden="true"
        />
        {{ t('application.back') }}
      </RouterLink>

      <h1 class="mt-3 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
        {{ t('application.new.title') }}
      </h1>

      <p class="mt-2 text-sm text-fino-text-muted">
        {{ t('application.new.description') }}
      </p>
    </div>

    <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <div class="min-w-0 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
        <AppErrorState
          v-if="catalogError"
          :message="t('application.new.catalogError')"
          is-inline
          @retry="loadProducts"
        />

        <form
          v-else
          class="flex flex-col gap-5"
          novalidate
          :aria-busy="isCatalogLoading || isSubmitting"
          @submit.prevent="handleSubmit"
        >
          <SandboxPersonaField
            input-id="application-product"
            :label="t('application.new.product')"
            :error="errors.product ?? null"
          >
            <Select
              v-model="form.product"
              input-id="application-product"
              :options="productOptions"
              option-label="name"
              option-value="code"
              :placeholder="t('application.new.productPlaceholder')"
              :loading="isCatalogLoading"
              :invalid="Boolean(errors.product)"
              :disabled="isSubmitting"
              fluid
            />
          </SandboxPersonaField>

          <!-- Сумма варианта меньше желаемой — говорим прямо и даём подать на всю -->
          <div
            v-if="isWantedNoticeVisible"
            class="flex flex-col gap-3 rounded-2xl bg-amber-500/10 p-4 text-sm text-fino-text"
            role="status"
          >
            <p class="leading-relaxed">
              {{ wantedNotice }}
            </p>

            <button
              type="button"
              class="inline-flex min-h-10 w-fit cursor-pointer items-center gap-2 rounded-xl border border-fino-border
                     bg-fino-surface px-4 text-sm font-semibold text-fino-text transition-colors hover:bg-fino-surface-hover
                     disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none"
              :disabled="isSubmitting"
              @click="applyWantedAmount"
            >
              {{ t('application.new.wanted.action', { wanted: formatMoney(wantedAmount ?? 0) }) }}
            </button>
          </div>

          <div class="grid grid-cols-1 gap-5 sm:grid-cols-2">
            <SandboxPersonaField
              input-id="application-amount"
              :label="t('application.new.amount')"
              :hint="amountHint"
              :error="errors.amount ?? null"
            >
              <InputNumber
                v-model="form.amount"
                input-id="application-amount"
                :min="selectedProduct?.amountMin ?? 1"
                :max="selectedProduct?.amountMax"
                :max-fraction-digits="0"
                suffix=" ₽"
                :locale="locale"
                :invalid="Boolean(errors.amount)"
                :disabled="!form.product || isSubmitting"
                fluid
              />
            </SandboxPersonaField>

            <SandboxPersonaField
              input-id="application-term"
              :label="t('application.new.term')"
              :hint="termHint"
              :error="errors.termMonths ?? null"
            >
              <InputNumber
                v-model="form.termMonths"
                input-id="application-term"
                :min="selectedProduct?.termMonthsMin"
                :max="selectedProduct?.termMonthsMax"
                :max-fraction-digits="0"
                :suffix="termSuffix"
                :locale="locale"
                :invalid="Boolean(errors.termMonths)"
                :disabled="!form.product || isSubmitting"
                fluid
              />
            </SandboxPersonaField>
          </div>

          <SandboxPersonaField
            v-if="goalOptions.length"
            input-id="application-goal"
            :label="t('application.new.goal')"
            :hint="isBankChoice ? undefined : t('application.new.goalHint')"
            :error="errors.goal ?? null"
          >
            <Select
              v-model="form.goal"
              input-id="application-goal"
              :options="goalOptions"
              option-label="label"
              option-value="code"
              :placeholder="t('application.new.goalPlaceholder')"
              :invalid="Boolean(errors.goal)"
              :show-clear="!isBankChoice"
              :disabled="isSubmitting"
              fluid
            />
          </SandboxPersonaField>

          <label class="flex cursor-pointer items-start gap-3 rounded-2xl border border-fino-border p-3 text-sm text-fino-text">
            <Checkbox
              v-model="form.consentBki"
              binary
              :disabled="isSubmitting"
              class="mt-0.5 shrink-0"
            />

            <span class="min-w-0">
              <span class="block font-semibold">{{ t('application.new.consent') }}</span>
              <span class="mt-0.5 block text-xs leading-relaxed text-fino-text-muted">
                {{ t('application.new.consentHint') }}
              </span>
            </span>
          </label>

          <Message
            v-if="errorMessage"
            severity="error"
            role="alert"
          >
            {{ errorMessage }}
          </Message>

          <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <button
              type="button"
              class="inline-flex min-h-12 cursor-pointer items-center justify-center rounded-xl border
                     border-fino-border bg-fino-surface px-5 py-3 text-sm font-semibold text-fino-text
                     transition-colors duration-200 hover:bg-fino-surface-hover
                     disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              :disabled="isSubmitting"
              @click="handleCancel"
            >
              {{ t('application.new.cancel') }}
            </button>

            <button
              type="submit"
              class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl
                     bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast
                     transition-all duration-200 hover:opacity-90 active:scale-95
                     disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              :disabled="isSubmitting || isCatalogLoading"
              :aria-busy="isSubmitting"
            >
              <i
                :class="isSubmitting ? 'pi pi-spinner pi-spin' : 'pi pi-send'"
                class="text-xs"
                aria-hidden="true"
              />
              {{ t('application.new.submit') }}
            </button>
          </div>
        </form>
      </div>

      <!-- Данные компании и продукта подставляются автоматически -->
      <aside class="flex min-w-0 flex-col gap-4">
        <article class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm">
          <h2 class="text-sm font-semibold text-fino-text">
            {{ t('application.new.company') }}
          </h2>

          <p class="mt-3 break-words text-base font-bold text-fino-text">
            {{ demoPersona?.organizationName }}
          </p>

          <p class="mt-1 text-sm text-fino-text-muted">
            {{ t('application.new.inn', { inn }) }}
          </p>
        </article>

        <article
          v-if="selectedProduct"
          class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
        >
          <h2 class="text-sm font-semibold text-fino-text">
            {{ selectedProduct.name }}
          </h2>

          <p
            v-if="rateText"
            class="mt-2 text-sm font-semibold text-fino-text"
          >
            {{ rateText }}
          </p>

          <ul class="mt-3 flex flex-col gap-2">
            <li
              v-for="benefit in selectedProduct.benefits"
              :key="benefit"
              class="flex items-start gap-2 text-sm text-fino-text"
            >
              <i
                class="pi pi-check mt-0.5 text-xs text-primary"
                aria-hidden="true"
              />
              <span class="min-w-0 break-words">{{ benefit }}</span>
            </li>
          </ul>

          <p class="mt-3 border-t border-fino-border pt-3 text-xs text-fino-text-muted">
            {{ selectedProduct.decisionText }}
          </p>
        </article>
      </aside>
    </div>
  </div>
</template>
