<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import PreApprovedProductsCardSkeleton from './PreApprovedProductsCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

const props = defineProps<{
  products: CreditProductInterface[]
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  apply: [product: CreditProductInterface]
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.products.length)

const productRows = computed(() =>
  props.products.map((product) => {
    const rate = formatPercent(product.rate)

    return {
      product,
      terms: [
        t('preApproved.amount', { amount: formatCurrency(product.amount, product.currency) }),
        product.isRateFrom ? t('preApproved.rateFrom', { rate }) : rate,
      ].join(' · '),
      applyLabel: t('preApproved.applyLabel', { name: product.name }),
    }
  }),
)

// Подпись о предварительном решении — только если её подтверждают данные API
const isPreliminary = computed(() => props.products.some((product) => product.isPreliminary))

function handleApply(product: CreditProductInterface) {
  emit('apply', product)
}

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm"
  >
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('preApproved.title') }}
    </h2>

    <PreApprovedProductsCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('preApproved.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <p
      v-else-if="!productRows.length"
      class="text-sm text-fino-text-muted"
    >
      {{ t('preApproved.empty') }}
    </p>

    <template v-else>
      <ul class="flex flex-col divide-y divide-fino-border">
        <li
          v-for="row in productRows"
          :key="row.product.id"
          class="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
        >
          <div class="min-w-0 flex-1">
            <p class="break-words text-sm font-semibold text-fino-text">
              {{ row.product.name }}
            </p>

            <p class="mt-0.5 break-words text-xs text-fino-text-muted">
              {{ row.terms }}
            </p>
          </div>

          <button
            type="button"
            class="shrink-0 cursor-pointer rounded-lg border border-fino-border px-3 py-1.5
                   text-xs font-semibold text-fino-text transition-colors duration-200
                   hover:border-primary hover:text-primary
                   focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
                   motion-reduce:transition-none"
            :aria-label="row.applyLabel"
            @click="handleApply(row.product)"
          >
            {{ t('preApproved.apply') }}
          </button>
        </li>
      </ul>

      <p
        v-if="isPreliminary"
        class="mt-auto flex items-center gap-1.5 text-xs text-fino-text-muted"
      >
        <i
          class="pi pi-info-circle text-xs"
          aria-hidden="true"
        />
        {{ t('preApproved.preliminary') }}
      </p>
    </template>
  </article>
</template>
