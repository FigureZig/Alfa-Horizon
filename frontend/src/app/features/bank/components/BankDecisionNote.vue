<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankNoteInterface } from '@/app/types/bank/bank-note-interface'

const props = defineProps<{
  note: BankNoteInterface
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatDateTime, formatTerm } = useFormatters()

const title = computed(() => t(`bank.note.action.${props.note.action}`))

const at = computed(() =>
  formatDateTime(props.note.at, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
)

const offerText = computed(() => {
  const offer = props.note.offer

  return offer
    ? t('bank.confirm.offer', {
      product: offer.productName,
      amount: formatCurrency(offer.amount, 'RUB'),
      term: formatTerm(offer.termMonths),
      rate: formatPercent(offer.rate),
    })
    : ''
})

const secondKeyText = computed(() => {
  const key = props.note.secondKey

  return key ? t(key.isApproved ? 'bank.note.secondKeyApproved' : 'bank.note.secondKeyReturned') : ''
})
</script>

<template>
  <article class="flex flex-col gap-2 rounded-2xl p-4 border-2 border-fino-line">
    <div class="flex flex-wrap items-center justify-between gap-2">
      <p class="text-sm font-semibold text-fino-text">
        {{ title }}
      </p>

      <p class="text-xs text-fino-text-muted">
        {{ at }}
      </p>
    </div>

    <p
      v-if="offerText"
      class="break-words text-sm text-fino-text"
    >
      {{ offerText }}
    </p>

    <p
      v-if="note.comment"
      class="break-words rounded-xl bg-fino-surface-secondary p-3 text-sm text-fino-text"
    >
      {{ note.comment }}
    </p>

    <p
      v-if="secondKeyText"
      class="flex items-center gap-1.5 text-xs font-semibold text-fino-text-muted"
    >
      <i
        class="pi pi-key text-xs"
        aria-hidden="true"
      />
      {{ secondKeyText }}
    </p>
  </article>
</template>
