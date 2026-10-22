<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CatalogProductInterface } from '@/app/types/catalog/catalog-product-interface'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'
import type { Nullable } from '@/app/types/nullable'

const MAX_BENEFITS = 3

const props = defineProps<{
  product: CatalogProductInterface
  inn: string
  preApproved: Nullable<CreditProductInterface>
  isSelected: boolean
}>()

const emit = defineEmits<{
  calculate: [productCode: CatalogProductInterface['code']]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const rateFrom = computed(() => t('credits.products.rateFrom', { rate: formatPercent(props.product.rateFrom) }))

const amountRange = computed(() => t('credits.products.amountRange', {
  min: formatCurrency(props.product.amountMin, 'RUB', true),
  max: formatCurrency(props.product.amountMax, 'RUB', true),
}))

const termRange = computed(() =>
  props.product.termMonthsMin === props.product.termMonthsMax
    ? t('credits.products.termFixed', { months: props.product.termMonthsMin })
    : t('credits.products.termRange', { min: props.product.termMonthsMin, max: props.product.termMonthsMax }),
)

const preApprovedLimit = computed(() =>
  props.preApproved ? formatCurrency(props.preApproved.amount, props.preApproved.currency) : '',
)

const benefits = computed(() => props.product.benefits.slice(0, MAX_BENEFITS))

// Заявка по предодобренному предложению открывается с его суммой и сроком, иначе — с минимумом продукта
const applyRoute = computed(() => ({
  name: 'application-new',
  params: { inn: props.inn },
  query: {
    product: props.product.code,
    amount: props.preApproved?.amount ?? props.product.amountMin,
    term: props.preApproved?.termMonths ?? props.product.termMonthsMin,
  },
}))

function handleCalculate() {
  emit('calculate', props.product.code)
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border bg-fino-surface p-5 shadow-sm
           transition-all duration-300 motion-reduce:transition-none"
    :class="isSelected ? 'border-primary ring-1 ring-primary' : 'border-fino-border'"
  >
    <div class="flex items-start justify-between gap-3">
      <h3 class="min-w-0 break-words text-base font-bold tracking-tight text-fino-text">
        {{ product.name }}
      </h3>

      <span class="shrink-0 rounded-lg bg-fino-accent px-2.5 py-1 text-xs font-semibold text-primary">
        {{ rateFrom }}
      </span>
    </div>

    <p
      v-if="preApproved"
      class="flex items-center gap-2 rounded-xl bg-green-500/10 px-3 py-2 text-xs font-semibold
             text-green-700 dark:text-green-400"
    >
      <i
        class="pi pi-verified text-sm"
        aria-hidden="true"
      />
      {{ t('credits.products.preApproved', { amount: preApprovedLimit }) }}
    </p>

    <dl class="grid grid-cols-2 gap-3 text-sm">
      <div class="min-w-0">
        <dt class="text-xs text-fino-text-muted">
          {{ t('credits.products.amount') }}
        </dt>
        <dd class="mt-0.5 break-words font-semibold text-fino-text">
          {{ amountRange }}
        </dd>
      </div>

      <div class="min-w-0">
        <dt class="text-xs text-fino-text-muted">
          {{ t('credits.products.term') }}
        </dt>
        <dd class="mt-0.5 break-words font-semibold text-fino-text">
          {{ termRange }}
        </dd>
      </div>
    </dl>

    <ul class="flex flex-col gap-1.5">
      <li
        v-for="benefit in benefits"
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

    <p class="text-xs leading-relaxed text-fino-text-muted">
      {{ product.decisionText }}
    </p>

    <div class="mt-auto grid grid-cols-2 gap-2 pt-1">
      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border
               border-fino-border bg-fino-surface px-3 py-2 text-sm font-semibold text-fino-text
               transition-colors duration-200 hover:bg-fino-surface-hover motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :aria-pressed="isSelected"
        @click="handleCalculate"
      >
        <i
          class="pi pi-calculator text-xs"
          aria-hidden="true"
        />
        {{ t('credits.products.calculate') }}
      </button>

      <RouterLink
        :to="applyRoute"
        class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-3 py-2
               text-sm font-semibold text-primary-contrast transition-all duration-200
               hover:opacity-90 active:scale-95 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        {{ t('credits.products.apply') }}
      </RouterLink>
    </div>
  </article>
</template>
