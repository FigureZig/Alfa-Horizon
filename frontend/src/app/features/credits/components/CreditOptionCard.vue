<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CompanyOfferOptionInterface } from '@/app/types/company/company-offers-interface'

const props = defineProps<{
  option: CompanyOfferOptionInterface
  // Рекомендованный вариант: крупно и с акцентом
  isFeatured: boolean
}>()

const emit = defineEmits<{
  apply: [option: CompanyOfferOptionInterface]
  calculate: [option: CompanyOfferOptionInterface]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

// Сумма под запрос, а без него — максимум по данным банка
const shownAmount = computed(() => props.option.amount ?? props.option.maxAmount)

const amountText = computed(() => {
  if (shownAmount.value === null) return ''

  return props.option.amount !== null
    ? formatCurrency(shownAmount.value, 'RUB')
    : t('credits.options.upTo', { amount: formatCurrency(shownAmount.value, 'RUB') })
})

const conditions = computed(() => {
  const { rate, payment, termMonths, isRevolving } = props.option
  const parts: string[] = []

  if (rate !== null) parts.push(t('credits.options.rate', { rate: formatPercent(rate) }))
  if (termMonths !== null) parts.push(t('application.term', termMonths))
  if (payment !== null && !isRevolving) parts.push(t('credits.options.payment', { payment: formatCurrency(payment, 'RUB') }))

  return parts.join(' · ')
})

const stateClass = computed(() =>
  props.option.rank === 0
    ? 'bg-green-500/10 text-green-700 dark:text-green-400'
    : 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
)

function handleApply() {
  emit('apply', props.option)
}

function handleCalculate() {
  emit('calculate', props.option)
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border p-5 shadow-sm sm:p-6"
    :class="isFeatured
      ? 'border-primary/30 bg-linear-to-br from-fino-accent to-fino-surface'
      : 'border-fino-border bg-fino-surface'"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h3
          class="break-words font-bold tracking-tight text-fino-text"
          :class="isFeatured ? 'text-xl' : 'text-base'"
        >
          {{ option.name }}
        </h3>

        <p
          v-if="isFeatured"
          class="mt-1 inline-flex items-center gap-1.5 text-xs font-semibold text-primary"
        >
          <i
            class="pi pi-star-fill text-xs"
            aria-hidden="true"
          />
          {{ t('credits.options.recommended') }}
        </p>
      </div>

      <span
        class="shrink-0 rounded-full px-3 py-1 text-xs font-semibold"
        :class="stateClass"
      >
        {{ t(`credits.options.state.${option.label}`) }}
      </span>
    </div>

    <div>
      <p
        class="break-words font-bold tracking-tight text-fino-text"
        :class="isFeatured ? 'text-3xl sm:text-4xl' : 'text-2xl'"
      >
        {{ amountText }}
      </p>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ conditions }}
      </p>
    </div>

    <!-- Что понадобится: поручитель, залог, документы -->
    <ul
      v-if="option.needs.length"
      class="flex flex-wrap gap-2"
    >
      <li
        v-for="need in option.needs"
        :key="need"
        class="rounded-lg bg-fino-surface-secondary px-2.5 py-1 text-xs font-medium text-fino-text"
      >
        {{ need }}
      </li>
    </ul>

    <div class="flex flex-col gap-2 sm:flex-row">
      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
               font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90 active:scale-95
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        :aria-label="t('credits.options.applyLabel', { name: option.name })"
        @click="handleApply"
      >
        {{ t('credits.options.apply') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </button>

      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-fino-border
               bg-fino-surface px-5 text-sm font-semibold text-fino-text transition-colors duration-200
               hover:bg-fino-surface-hover focus-visible:outline-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        @click="handleCalculate"
      >
        <i
          class="pi pi-calculator text-xs"
          aria-hidden="true"
        />
        {{ t('credits.options.calculate') }}
      </button>
    </div>
  </article>
</template>
