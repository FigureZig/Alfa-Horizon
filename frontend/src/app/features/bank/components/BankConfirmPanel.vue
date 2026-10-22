<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Textarea from 'primevue/textarea'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankNoteInterface } from '@/app/types/bank/bank-note-interface'
import type { BankConfirmFormInterface } from '@/app/types/bank/bank-decision-form-interface'
import type { Nullable } from '@/app/types/nullable'

const COMMENT_MAX_LENGTH = 2000

const props = defineProps<{
  pending: BankNoteInterface
  pendingCommand: Nullable<string>
}>()

const emit = defineEmits<{
  confirm: [form: BankConfirmFormInterface]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatDateTime } = useFormatters()

const comment = ref('')

const isBusy = computed(() => props.pendingCommand !== null)

const offerText = computed(() => {
  const offer = props.pending.offer

  if (!offer) return ''

  return t('bank.confirm.offer', {
    product: offer.productName,
    amount: formatCurrency(offer.amount, 'RUB'),
    term: t('application.term', offer.termMonths),
    rate: formatPercent(offer.rate),
  })
})

const limitText = computed(() =>
  props.pending.limit ? t('bank.confirm.limit', { limit: formatCurrency(props.pending.limit, 'RUB') }) : '',
)

const proposedAt = computed(() =>
  formatDateTime(props.pending.at, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
)

function handleApprove() {
  emit('confirm', { isApproved: true, comment: comment.value })
}

function handleReturn() {
  emit('confirm', { isApproved: false, comment: comment.value })
}
</script>

<template>
  <section class="flex flex-col gap-5">
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('bank.confirm.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('bank.confirm.description') }}
      </p>
    </div>

    <div class="flex flex-col gap-2 rounded-2xl border border-primary p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
        {{ t('bank.confirm.proposed', { date: proposedAt }) }}
      </p>

      <p class="break-words text-base font-bold text-fino-text">
        {{ offerText }}
      </p>

      <p
        v-if="limitText"
        class="text-xs text-fino-text-muted"
      >
        {{ limitText }}
      </p>

      <p
        v-if="pending.comment"
        class="mt-1 break-words rounded-xl bg-fino-surface-secondary p-3 text-sm text-fino-text"
      >
        {{ pending.comment }}
      </p>
    </div>

    <SandboxPersonaField
      input-id="bank-confirm-comment"
      :label="t('bank.decision.comment')"
      :error="null"
    >
      <Textarea
        id="bank-confirm-comment"
        v-model="comment"
        :maxlength="COMMENT_MAX_LENGTH"
        rows="2"
        auto-resize
        :disabled="isBusy"
        fluid
      />
    </SandboxPersonaField>

    <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <button
        type="button"
        class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary
               px-5 py-3 text-sm font-semibold text-primary-contrast transition-all duration-200
               hover:opacity-90 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60
               motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isBusy"
        :aria-busy="pendingCommand === 'confirm'"
        @click="handleApprove"
      >
        <i
          :class="pendingCommand === 'confirm' ? 'pi pi-spinner pi-spin' : 'pi pi-key'"
          class="text-xs"
          aria-hidden="true"
        />
        {{ t('bank.confirm.approve') }}
      </button>

      <button
        type="button"
        class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl border
               border-fino-border bg-fino-surface px-5 py-3 text-sm font-semibold text-fino-text
               transition-colors duration-200 hover:bg-fino-surface-hover
               disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isBusy"
        :aria-busy="pendingCommand === 'return'"
        @click="handleReturn"
      >
        <i
          :class="pendingCommand === 'return' ? 'pi pi-spinner pi-spin' : 'pi pi-replay'"
          class="text-xs"
          aria-hidden="true"
        />
        {{ t('bank.confirm.return') }}
      </button>
    </div>
  </section>
</template>
