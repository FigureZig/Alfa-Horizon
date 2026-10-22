<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

const props = defineProps<{
  product: CreditProductInterface
}>()

const emit = defineEmits<{
  closeGap: [product: CreditProductInterface]
  showOptions: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const amount = computed(() => formatCurrency(props.product.amount, props.product.currency))

const conditions = computed(() => [
  t('creditOffer.rate', { rate: formatPercent(props.product.rate) }),
  t('creditOffer.term', props.product.termMonths),
].join(' · '))

function handleCloseGap() {
  emit('closeGap', props.product)
}

function handleShowOptions() {
  emit('showOptions')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-5 rounded-3xl bg-violet-600 p-5 text-white
           shadow-sm sm:p-6 dark:bg-violet-700"
    :aria-label="t('creditOffer.label')"
  >
    <span
      class="inline-flex w-fit items-center gap-1.5 rounded-full bg-white/15
             px-3 py-1 text-xs font-semibold"
    >
      <i
        class="pi pi-check-circle text-xs"
        aria-hidden="true"
      />
      {{ t('creditOffer.eyebrow') }}
    </span>

    <div class="min-w-0">
      <h2 class="break-words text-lg font-semibold">
        {{ product.name }}
      </h2>

      <p class="mt-2 break-words text-3xl font-bold tracking-tight">
        {{ amount }}
      </p>

      <p class="mt-1 text-sm text-white/80">
        {{ conditions }}
      </p>
    </div>

    <ul
      v-if="product.benefits.length"
      class="flex flex-col gap-2.5 border-t border-white/20 pt-4"
    >
      <li
        v-for="benefit in product.benefits"
        :key="benefit"
        class="flex items-start gap-2 text-sm"
      >
        <i
          class="pi pi-check mt-0.5 text-xs text-white/80"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ benefit }}</span>
      </li>
    </ul>

    <div class="mt-auto flex flex-col gap-2.5">
      <button
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2
               rounded-xl bg-white px-5 py-3 text-center text-sm font-semibold text-violet-700
               transition-all duration-200 hover:bg-white/90 active:scale-95
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white
               motion-reduce:transition-none"
        @click="handleCloseGap"
      >
        <i
          class="pi pi-bolt text-xs"
          aria-hidden="true"
        />
        {{ t('creditOffer.closeGap') }}
      </button>

      <button
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center
               rounded-xl border border-white/30 px-5 py-3 text-center text-sm font-semibold
               transition-colors duration-200 hover:bg-white/10
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white
               motion-reduce:transition-none"
        @click="handleShowOptions"
      >
        {{ t('creditOffer.otherOptions') }}
      </button>
    </div>
  </article>
</template>
