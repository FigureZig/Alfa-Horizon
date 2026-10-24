<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ApplicationOfferInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  proposal: Nullable<ApplicationOfferInterface>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatTerm } = useFormatters()

const proposalText = computed(() =>
  props.proposal
    ? t('bank.engine.proposal', {
      amount: formatCurrency(props.proposal.amount, 'RUB'),
      term: formatTerm(props.proposal.termMonths),
      rate: formatPercent(props.proposal.rate),
    })
    : t('bank.engine.none'),
)
</script>

<template>
  <!-- Подсказка машины — после фактов и свёрнута: сначала своё суждение специалиста -->
  <details class="group min-w-0 rounded-3xl border border-fino-border bg-fino-surface shadow-sm">
    <summary
      class="flex cursor-pointer items-center justify-between gap-3 rounded-3xl px-5 py-4 marker:content-none
             focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span class="flex min-w-0 items-center gap-3">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-surface-secondary text-fino-text-muted"
          aria-hidden="true"
        >
          <i class="pi pi-cog" />
        </span>

        <span class="min-w-0">
          <span class="block text-sm font-semibold text-fino-text">{{ t('bank.engine.title') }}</span>
          <span class="block text-xs text-fino-text-muted">{{ t('bank.engine.hint') }}</span>
        </span>
      </span>

      <i
        class="pi pi-chevron-down shrink-0 text-xs text-fino-text-muted transition-transform duration-200
               group-open:rotate-180 motion-reduce:transition-none"
        aria-hidden="true"
      />
    </summary>

    <p class="px-5 pb-5 text-sm text-fino-text">
      {{ proposalText }}
    </p>
  </details>
</template>
