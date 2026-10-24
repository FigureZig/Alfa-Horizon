<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CompanyOfferOptionInterface } from '@/app/types/company/company-offers-interface'

const props = defineProps<{
  option: CompanyOfferOptionInterface
  // Рекомендованный вариант: крупно и с акцентом
  isFeatured: boolean
  // Банк ещё не видел кредитную историю: сумма — «до», ставка — предварительная
  isPreliminary: boolean
  // Расчёт платежа раскрыт внутри этого варианта
  isCalculatorOpen: boolean
  // Подсветка после «Пусть банк подберёт»: вариант, который выбрал бы банк
  isHighlighted?: boolean
}>()

const emit = defineEmits<{
  select: [option: CompanyOfferOptionInterface]
  toggleCalculator: [option: CompanyOfferOptionInterface]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatTerm } = useFormatters()

// Сумма под запрос, а без него — максимум по данным банка
const shownAmount = computed(() => props.option.amount ?? props.option.maxAmount)

// Без кредитной истории сумма — потолок, а не обещание
const amountText = computed(() => {
  if (shownAmount.value === null) return ''

  const amount = formatCurrency(shownAmount.value, 'RUB')

  return props.option.amount !== null && !props.isPreliminary ? amount : t('credits.options.upTo', { amount })
})

const conditions = computed(() => {
  const { rate, payment, termMonths, isRevolving } = props.option
  const parts: string[] = []

  if (rate !== null) {
    const rateText = t('credits.options.rate', { rate: formatPercent(rate) })

    parts.push(props.isPreliminary ? t('credits.options.ratePreliminary', { rate: rateText }) : rateText)
  }

  if (termMonths !== null) parts.push(formatTerm(termMonths))
  if (payment !== null && !isRevolving) parts.push(t('credits.options.payment', { payment: formatCurrency(payment, 'RUB') }))

  return parts.join(' · ')
})

const stateClass = computed(() =>
  props.option.rank === 0
    ? 'border-2 border-fino-line bg-fino-lime text-[#111]'
    : 'border-2 border-fino-line bg-fino-amber text-[#111]',
)

function handleSelect() {
  emit('select', props.option)
}

function handleToggleCalculator() {
  emit('toggleCalculator', props.option)
}
</script>

<template>
  <article
    class="relative flex min-w-0 flex-col gap-4 card-key p-5 transition-shadow duration-500 sm:p-6
           motion-reduce:transition-none"
    :class="[
      isFeatured ? 'bg-fino-lime-soft' : '',
      { 'ring-4 ring-fino-violet/40': isHighlighted },
    ]"
  >
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <h3
          class="break-words font-extrabold text-fino-text"
          :class="isFeatured ? 'text-2xl' : 'text-lg'"
        >
          {{ option.name }}
        </h3>

        <!-- Рекомендация банка — наклонным стикером, как в макете -->
        <p
          v-if="isFeatured"
          class="mt-2 inline-flex -rotate-2 items-center gap-1.5 rounded-xl border-2 border-fino-line bg-fino-lime px-3
                 py-1 font-display text-sm font-black text-[#111] shadow-[3px_3px_0_var(--fino-shadow)]"
        >
          <i
            class="pi pi-star-fill text-xs"
            aria-hidden="true"
          />
          {{ t('credits.options.recommended') }}
        </p>
      </div>

      <span
        class="shrink-0 rounded-full px-3 py-1 font-mono text-xs font-bold"
        :class="stateClass"
      >
        {{ t(`credits.options.state.${option.label}`) }}
      </span>
    </div>

    <div>
      <p
        class="break-words font-display font-black tracking-tight text-fino-text tabular-nums"
        :class="isFeatured ? 'text-4xl sm:text-5xl' : 'text-3xl'"
      >
        {{ amountText }}
      </p>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ conditions }}
      </p>

      <!-- Что значит плашка статуса: «Доступен» и «С условиями» без пояснения не различить -->
      <p class="mt-2 text-xs text-fino-text-muted">
        {{ t(`credits.options.stateHint.${option.label}`) }}
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

    <!-- Одно действие: выбрать вариант; расчёт — по запросу, внутри варианта -->
    <div class="flex flex-col gap-2 sm:flex-row sm:items-center">
      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
               font-semibold text-primary-contrast focus-visible:outline-2 focus-visible:outline-offset-2
               focus-visible:outline-primary btn-key"
        :aria-label="t('credits.options.selectLabel', { name: option.name })"
        @click="handleSelect"
      >
        {{ t('credits.options.select') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </button>

      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl px-4 text-sm
               font-semibold text-fino-text-muted transition-colors duration-200 hover:bg-fino-surface-hover
               hover:text-fino-text focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
        :aria-expanded="isCalculatorOpen"
        @click="handleToggleCalculator"
      >
        {{ t('credits.options.calculate') }}
        <i
          class="pi pi-chevron-down text-xs transition-transform duration-200 motion-reduce:transition-none"
          :class="{ 'rotate-180': isCalculatorOpen }"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Расчёт платежа и график — для выбранного варианта -->
    <div
      v-if="isCalculatorOpen"
      class="border-t border-fino-border pt-5"
    >
      <slot name="calculator" />
    </div>
  </article>
</template>
