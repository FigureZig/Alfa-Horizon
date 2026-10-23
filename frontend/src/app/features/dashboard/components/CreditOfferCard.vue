<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CashGapOfferInterface } from '@/app/types/company/cash-forecast-interface'

const MAX_BENEFITS = 2

const props = defineProps<{
  offer: CashGapOfferInterface
}>()

const emit = defineEmits<{
  closeGap: []
  showOptions: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const amount = computed(() => formatCurrency(props.offer.amount, props.offer.currency))

const conditions = computed(() => [
  t('creditOffer.rate', { rate: formatPercent(props.offer.rate) }),
  t('creditOffer.term', props.offer.termMonths),
].join(' · '))

// Цена закрытия разрыва: сколько возьмём из лимита и сколько это стоит
const coverLine = computed(() => {
  const { cover, currency } = props.offer

  return cover
    ? t('creditOffer.cover', {
      amount: formatCurrency(cover.amount, currency),
      days: cover.days,
      interest: formatCurrency(cover.interest, currency),
    })
    : ''
})

const benefits = computed(() => props.offer.benefits.slice(0, MAX_BENEFITS))

function handleCloseGap() {
  emit('closeGap')
}

function handleShowOptions() {
  emit('showOptions')
}
</script>

<template>
  <article
    class="relative flex min-w-0 flex-col gap-5 overflow-hidden rounded-3xl border border-fino-border
           bg-linear-to-br from-fino-accent to-fino-surface p-5 shadow-sm sm:p-6"
    :aria-label="t('creditOffer.label')"
  >
    <span
      class="inline-flex w-fit items-center gap-1.5 rounded-full bg-fino-surface px-3 py-1 text-xs
             font-semibold text-primary shadow-sm"
    >
      <i
        class="pi pi-check-circle text-xs"
        aria-hidden="true"
      />
      {{ t('creditOffer.eyebrow') }}
    </span>

    <div class="min-w-0">
      <h2 class="break-words text-base font-semibold text-fino-text">
        {{ offer.name }}
      </h2>

      <p class="mt-1 break-words text-3xl font-bold tracking-tight text-fino-text">
        {{ amount }}
      </p>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ conditions }}
      </p>
    </div>

    <p
      v-if="coverLine"
      class="rounded-2xl bg-fino-surface px-4 py-3 text-sm leading-relaxed text-fino-text shadow-sm"
    >
      {{ coverLine }}
    </p>

    <ul
      v-if="benefits.length"
      class="flex flex-col gap-2"
    >
      <li
        v-for="benefit in benefits"
        :key="benefit"
        class="flex items-start gap-2 text-sm text-fino-text-muted"
      >
        <i
          class="pi pi-check mt-0.5 text-xs text-primary"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ benefit }}</span>
      </li>
    </ul>

    <div class="mt-auto flex flex-col gap-2">
      <button
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary
               px-5 py-3 text-center text-sm font-semibold text-primary-contrast shadow-sm transition-all
               duration-200 hover:opacity-90 active:scale-95 focus-visible:outline-2
               focus-visible:outline-offset-2 focus-visible:outline-primary motion-reduce:transition-none"
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
        class="inline-flex min-h-11 w-full cursor-pointer items-center justify-center rounded-xl px-5 py-2.5
               text-center text-sm font-semibold text-fino-text-muted transition-colors duration-200
               hover:bg-fino-surface hover:text-fino-text focus-visible:outline-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        @click="handleShowOptions"
      >
        {{ t('creditOffer.otherOptions') }}
      </button>
    </div>
  </article>
</template>
