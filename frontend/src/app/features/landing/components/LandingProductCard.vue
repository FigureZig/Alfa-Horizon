<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CatalogProductInterface } from '@/app/types/catalog/catalog-product-interface'

const MAX_BENEFITS = 2

const props = defineProps<{
  product: CatalogProductInterface
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

const benefits = computed(() => props.product.benefits.slice(0, MAX_BENEFITS))
</script>

<template>
  <article
    class="group flex h-full min-w-0 flex-col gap-5 rounded-3xl border border-fino-border
           bg-fino-surface p-6 shadow-sm transition-all duration-300
           hover:-translate-y-1 hover:border-primary/40 hover:shadow-md
           motion-reduce:transition-none motion-reduce:hover:translate-y-0"
  >
    <div class="flex items-start justify-between gap-3">
      <h3 class="min-w-0 break-words text-lg font-bold tracking-tight text-fino-text">
        {{ product.name }}
      </h3>

      <span
        class="shrink-0 rounded-full bg-fino-accent px-3 py-1 text-xs font-semibold
               whitespace-nowrap text-primary"
      >
        {{ rateFrom }}
      </span>
    </div>

    <div>
      <p class="break-words text-2xl font-bold tracking-tight text-fino-text">
        {{ amountRange }}
      </p>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ termRange }}
      </p>
    </div>

    <p
      v-if="product.decisionText"
      class="line-clamp-2 text-sm leading-relaxed text-fino-text-muted first-letter:uppercase"
    >
      {{ product.decisionText }}
    </p>

    <ul
      v-if="benefits.length"
      class="mt-auto flex flex-col gap-2 border-t border-fino-border pt-4"
    >
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
  </article>
</template>
