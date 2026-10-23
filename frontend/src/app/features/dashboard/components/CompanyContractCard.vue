<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useFormatters } from '@/app/composables/useFormatters'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CompanyContractInterface } from '@/app/types/company/cash-forecast-interface'

const props = defineProps<{
  inn: string
  contract: CompanyContractInterface
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { formatCurrency, formatDate } = useFormatters()

const price = computed(() => formatCurrency(props.contract.price, 'RUB', true))

const details = computed(() => [
  props.contract.customer,
  props.contract.advancePercent !== null ? t('contractCard.advance', { percent: props.contract.advancePercent }) : '',
  props.contract.endDate ? t('contractCard.until', { date: formatDate(props.contract.endDate, { day: 'numeric', month: 'long', year: 'numeric' }) }) : '',
].filter(Boolean).join(' · '))

// Кредит на исполнение контракта: подбор открывается сразу с целью
function showContractCredit() {
  router.push({ name: 'credits', params: { inn: props.inn }, query: { goal: CreditGoalEnum.Contract } })
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm
           sm:flex-row sm:items-center sm:p-6"
  >
    <span class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-fino-accent text-primary">
      <i
        class="pi pi-file-check text-lg"
        aria-hidden="true"
      />
    </span>

    <div class="min-w-0 flex-1">
      <h2 class="break-words text-base font-bold tracking-tight text-fino-text">
        {{ t('contractCard.title', { price }) }}
      </h2>

      <p class="mt-1 break-words text-sm text-fino-text-muted">
        {{ details }}
      </p>
    </div>

    <button
      type="button"
      class="inline-flex min-h-11 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary
             px-5 text-sm font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90
             active:scale-95 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
             motion-reduce:transition-none"
      @click="showContractCredit"
    >
      {{ t('contractCard.action') }}
      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </button>
  </article>
</template>
