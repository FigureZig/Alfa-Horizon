<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import Textarea from 'primevue/textarea'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationAskEnum } from '@/app/types/application/application-ask-enum'
import { BankDecisionActionEnum } from '@/app/types/bank/bank-decision-action-enum'
import type {
  ApplicationOfferInterface,
  ApplicationRequestInterface,
} from '@/app/types/application/application-interface'
import type { BankDecisionFormInterface } from '@/app/types/bank/bank-decision-form-interface'
import type { Nullable } from '@/app/types/nullable'

const COMMENT_MAX_LENGTH = 2000
const MAX_TERM_MONTHS = 120
const DEFAULT_TERM_MONTHS = 12

const ASK_OPTIONS = [
  ApplicationAskEnum.Documents,
  ApplicationAskEnum.CollateralValue,
  ApplicationAskEnum.TurnoverData,
  ApplicationAskEnum.Guarantor,
  ApplicationAskEnum.CorpApproval,
]

const props = defineProps<{
  proposal: Nullable<ApplicationOfferInterface>
  request: ApplicationRequestInterface
  pendingCommand: Nullable<string>
}>()

const emit = defineEmits<{
  decide: [form: BankDecisionFormInterface]
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

// Условия подставляем из предложения движка, а если его нет — из запроса клиента
const form = reactive<BankDecisionFormInterface>({
  action: BankDecisionActionEnum.Approve,
  amount: props.proposal?.amount ?? props.request.amount,
  termMonths: props.proposal?.termMonths ?? props.request.termMonths ?? DEFAULT_TERM_MONTHS,
  asks: [ApplicationAskEnum.Documents],
  comment: '',
})

const isSubmitted = ref(false)

const isBusy = computed(() => props.pendingCommand !== null)
const isApprove = computed(() => form.action === BankDecisionActionEnum.Approve)
const isRequestInfo = computed(() => form.action === BankDecisionActionEnum.RequestInfo)
const isReject = computed(() => form.action === BankDecisionActionEnum.Reject)

const actionOptions = computed(() => [
  { value: BankDecisionActionEnum.Approve, label: t('bank.decision.action.approve') },
  { value: BankDecisionActionEnum.RequestInfo, label: t('bank.decision.action.request_info') },
  { value: BankDecisionActionEnum.Reject, label: t('bank.decision.action.reject') },
])

const askOptions = computed(() => ASK_OPTIONS.map((ask) => ({ value: ask, label: t(`application.infoRequest.ask.${ask}`) })))

const proposalText = computed(() =>
  props.proposal
    ? t('bank.decision.engineProposal', {
      amount: formatCurrency(props.proposal.amount, 'RUB'),
      term: t('application.term', props.proposal.termMonths),
      rate: formatPercent(props.proposal.rate),
    })
    : t('bank.decision.noEngineProposal'),
)

const errorText = computed(() => {
  if (!isSubmitted.value) return null

  if (isApprove.value) {
    const isAmountValid = form.amount !== null && form.amount > 0
    const isTermValid = form.termMonths !== null && form.termMonths > 0 && form.termMonths <= MAX_TERM_MONTHS

    return isAmountValid && isTermValid ? null : t('bank.decision.termsRequired')
  }

  if (isRequestInfo.value && !form.asks.length) return t('bank.decision.asksRequired')

  return null
})

const submitIcon = computed(() => {
  if (props.pendingCommand) return 'pi pi-spinner pi-spin'

  return isApprove.value ? 'pi pi-check' : isReject.value ? 'pi pi-times' : 'pi pi-send'
})

function handleSubmit() {
  isSubmitted.value = true

  if (errorText.value) return

  emit('decide', { ...form, asks: [...form.asks] })
}
</script>

<template>
  <form
    class="flex flex-col gap-5"
    novalidate
    @submit.prevent="handleSubmit"
  >
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('bank.decision.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('bank.decision.description') }}
      </p>
    </div>

    <p class="flex items-start gap-2 rounded-2xl bg-fino-surface-secondary p-3 text-sm text-fino-text">
      <i
        class="pi pi-microchip-ai mt-0.5 text-primary"
        aria-hidden="true"
      />
      <span class="min-w-0 break-words">{{ proposalText }}</span>
    </p>

    <SelectButton
      v-model="form.action"
      :options="actionOptions"
      option-label="label"
      option-value="value"
      :allow-empty="false"
      :disabled="isBusy"
      :aria-label="t('bank.decision.title')"
      class="grid w-full grid-cols-3 [&_.p-togglebutton]:min-w-0 [&_.p-togglebutton]:px-2
             [&_.p-togglebutton]:text-center [&_.p-togglebutton]:whitespace-normal"
    />

    <!-- Одобрить: цена риска остаётся, меняются сумма и срок -->
    <div
      v-if="isApprove"
      class="grid grid-cols-1 gap-4 sm:grid-cols-2"
    >
      <SandboxPersonaField
        input-id="bank-amount"
        :label="t('bank.decision.amount')"
        :error="null"
      >
        <InputNumber
          v-model="form.amount"
          input-id="bank-amount"
          :min="1"
          :max-fraction-digits="0"
          suffix=" ₽"
          :locale="locale"
          :invalid="isSubmitted && !form.amount"
          :disabled="isBusy"
          fluid
        />
      </SandboxPersonaField>

      <SandboxPersonaField
        input-id="bank-term"
        :label="t('bank.decision.term')"
        :hint="t('bank.decision.priceHint')"
        :error="null"
      >
        <InputNumber
          v-model="form.termMonths"
          input-id="bank-term"
          :min="1"
          :max="MAX_TERM_MONTHS"
          :max-fraction-digits="0"
          :suffix="` ${t('application.new.months')}`"
          :locale="locale"
          :invalid="isSubmitted && !form.termMonths"
          :disabled="isBusy"
          fluid
        />
      </SandboxPersonaField>

      <p class="text-xs leading-relaxed text-fino-text-muted sm:col-span-2">
        {{ t('bank.decision.authorityHint') }}
      </p>
    </div>

    <!-- Запросить данные: что именно нужно от клиента -->
    <fieldset
      v-else-if="isRequestInfo"
      class="flex flex-col gap-2"
    >
      <legend class="mb-1 text-sm font-semibold text-fino-text">
        {{ t('bank.decision.asks') }}
      </legend>

      <label
        v-for="option in askOptions"
        :key="option.value"
        class="flex cursor-pointer items-center gap-3 rounded-xl border border-fino-border px-3 py-2
               text-sm text-fino-text transition-colors hover:bg-fino-surface-hover
               has-[:checked]:border-primary has-[:checked]:bg-fino-accent
               motion-reduce:transition-none"
      >
        <Checkbox
          v-model="form.asks"
          :value="option.value"
          :disabled="isBusy"
        />
        <span class="min-w-0 break-words">{{ option.label }}</span>
      </label>
    </fieldset>

    <p
      v-else
      class="rounded-2xl bg-red-500/10 p-3 text-sm text-fino-text"
    >
      {{ t('bank.decision.rejectHint') }}
    </p>

    <SandboxPersonaField
      input-id="bank-comment"
      :label="t('bank.decision.comment')"
      :hint="t('bank.decision.commentHint')"
      :error="null"
    >
      <Textarea
        id="bank-comment"
        v-model="form.comment"
        :maxlength="COMMENT_MAX_LENGTH"
        rows="2"
        auto-resize
        :disabled="isBusy"
        fluid
      />
    </SandboxPersonaField>

    <Message
      v-if="errorText"
      severity="error"
      size="small"
      variant="simple"
    >
      {{ errorText }}
    </Message>

    <button
      type="submit"
      class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl px-5 py-3
             text-sm font-semibold transition-all duration-200 active:scale-95 sm:w-fit
             disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
             focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      :class="isReject
        ? 'border border-fino-border bg-fino-surface text-red-700 hover:bg-red-500/10 dark:text-red-400'
        : 'bg-primary text-primary-contrast hover:opacity-90'"
      :disabled="isBusy"
      :aria-busy="isBusy"
    >
      <i
        :class="submitIcon"
        class="text-xs"
        aria-hidden="true"
      />
      {{ t(`bank.decision.submit.${form.action}`) }}
    </button>
  </form>
</template>
