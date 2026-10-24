<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ApplicationOfferInterface } from '@/app/types/application/application-interface'

// У возобновляемого продукта (овердрафта) платежа и срока кредита нет: подключается лимит
const REVOLVING = 'revolving'

const props = defineProps<{
  visible: boolean
  offer: ApplicationOfferInterface
  isSubmitting: boolean
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  confirm: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const isLimit = computed(() => props.offer.repayment === REVOLVING)

const rows = computed(() => {
  const result = [
    { label: isLimit.value ? t('application.sign.limit') : t('application.sign.amount'), value: formatCurrency(props.offer.amount, 'RUB') },
    { label: t('application.offers.rate'), value: formatPercent(props.offer.rate) },
    { label: t('application.offers.termLabel'), value: t('application.term', props.offer.termMonths) },
  ]

  if (!isLimit.value) {
    result.push({ label: t('application.offers.payment'), value: formatCurrency(props.offer.payment, 'RUB') })
  }

  return result
})

function handleVisibleChange(visible: boolean) {
  emit('update:visible', visible)
}

function handleCancel() {
  emit('update:visible', false)
}

function handleConfirm() {
  emit('confirm')
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="!isSubmitting"
    :header="t('application.sign.title')"
    :style="{ width: '28rem', maxWidth: '94vw' }"
    @update:visible="handleVisibleChange"
  >
    <div class="flex flex-col gap-5">
      <div class="flex items-center gap-3 rounded-2xl bg-fino-accent p-4">
        <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-fino-surface text-primary">
          <i
            class="pi pi-file-edit"
            aria-hidden="true"
          />
        </span>

        <p class="min-w-0 break-words text-sm font-bold text-fino-text">
          {{ offer.productName }}
        </p>
      </div>

      <dl class="flex flex-col divide-y divide-fino-border">
        <div
          v-for="row in rows"
          :key="row.label"
          class="flex items-baseline justify-between gap-4 py-3 text-sm"
        >
          <dt class="text-fino-text-muted">
            {{ row.label }}
          </dt>
          <dd class="shrink-0 text-right font-semibold text-fino-text">
            {{ row.value }}
          </dd>
        </div>
      </dl>

      <!-- Подпись смоделирована: кейс просит обозначить это явно -->
      <p class="flex items-start gap-2 text-xs leading-relaxed text-fino-text-muted">
        <i
          class="pi pi-info-circle mt-0.5 shrink-0"
          aria-hidden="true"
        />
        {{ t('application.sign.note') }}
      </p>
    </div>

    <template #footer>
      <button
        type="button"
        class="cursor-pointer rounded-xl border border-fino-border px-4 py-2.5 text-sm font-semibold text-fino-text
               transition-colors hover:bg-fino-surface-hover disabled:cursor-not-allowed disabled:opacity-60
               motion-reduce:transition-none"
        :disabled="isSubmitting"
        @click="handleCancel"
      >
        {{ t('application.confirm.cancel') }}
      </button>

      <button
        type="button"
        class="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-semibold
               text-primary-contrast disabled:cursor-not-allowed disabled:opacity-60 btn-key"
        :disabled="isSubmitting"
        @click="handleConfirm"
      >
        <i
          v-if="isSubmitting"
          class="pi pi-spin pi-spinner text-xs"
          aria-hidden="true"
        />
        {{ t('application.sign.confirm') }}
      </button>
    </template>
  </Dialog>
</template>
