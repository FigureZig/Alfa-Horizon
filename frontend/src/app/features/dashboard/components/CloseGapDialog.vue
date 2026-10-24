<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import Dialog from 'primevue/dialog'
import Message from 'primevue/message'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CashGapInterface, CashGapOfferInterface } from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  visible: boolean
  offer: CashGapOfferInterface
  gap: Nullable<CashGapInterface>
  isSubmitting: boolean
  errorMessage: Nullable<string>
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  confirm: [consentBki: boolean]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatDate } = useFormatters()

// Согласие на запрос кредитной истории: без него условия предварительные
const consentBki = ref(true)

const limit = computed(() => formatCurrency(props.offer.amount, props.offer.currency))

const rows = computed(() => {
  const { cover } = props.offer
  const result: { label: string, value: string }[] = []

  if (props.gap) {
    result.push({
      label: t('closeGap.shortfall', { date: formatDate(props.gap.date, { day: 'numeric', month: 'long' }) }),
      value: formatCurrency(props.gap.amount, props.offer.currency),
    })
  }

  if (cover) {
    result.push(
      { label: t('closeGap.days'), value: t('closeGap.daysValue', cover.days) },
      { label: t('closeGap.interest'), value: t('closeGap.interestValue', { amount: formatCurrency(cover.interest, props.offer.currency) }) },
    )
  }

  result.push({ label: t('closeGap.rate'), value: t('closeGap.rateValue', { rate: formatPercent(props.offer.rate) }) })

  return result
})

function handleVisibleChange(visible: boolean) {
  emit('update:visible', visible)
}

function handleCancel() {
  emit('update:visible', false)
}

function handleConfirm() {
  emit('confirm', consentBki.value)
}

// Каждый раз открываем с согласием по умолчанию
watch(() => props.visible, (visible) => {
  if (visible) consentBki.value = true
})
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :closable="!isSubmitting"
    :header="t('closeGap.title')"
    :style="{ width: '28rem', maxWidth: '94vw' }"
    @update:visible="handleVisibleChange"
  >
    <div class="flex flex-col gap-5">
      <div class="flex items-center gap-3 rounded-2xl bg-fino-accent p-4">
        <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-fino-surface text-primary">
          <i
            class="pi pi-wallet"
            aria-hidden="true"
          />
        </span>

        <div class="min-w-0">
          <p class="break-words text-sm font-bold text-fino-text">
            {{ offer.name }}
          </p>
          <p class="text-sm text-fino-text-muted">
            {{ t('closeGap.limit', { limit }) }}
          </p>
        </div>
      </div>

      <dl class="flex flex-col divide-y divide-fino-border">
        <div
          v-for="row in rows"
          :key="row.label"
          class="flex items-baseline justify-between gap-4 py-3 text-sm"
        >
          <dt class="min-w-0 text-fino-text-muted">
            {{ row.label }}
          </dt>
          <dd class="shrink-0 text-right font-semibold text-fino-text">
            {{ row.value }}
          </dd>
        </div>
      </dl>

      <p class="text-xs leading-relaxed text-fino-text-muted">
        {{ t('closeGap.note') }}
      </p>

      <label class="flex cursor-pointer items-start gap-3 rounded-2xl p-3 text-sm border-2 border-fino-line">
        <Checkbox
          v-model="consentBki"
          binary
          :disabled="isSubmitting"
          class="mt-0.5 shrink-0"
        />

        <span class="min-w-0">
          <span class="block font-semibold text-fino-text">{{ t('closeGap.consent') }}</span>
          <span class="mt-0.5 block text-xs leading-relaxed text-fino-text-muted">{{ t('closeGap.consentHint') }}</span>
        </span>
      </label>

      <Message
        v-if="errorMessage"
        severity="error"
        role="alert"
      >
        {{ errorMessage }}
      </Message>
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
        {{ t('closeGap.cancel') }}
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
        {{ t('closeGap.confirm') }}
      </button>
    </template>
  </Dialog>
</template>
