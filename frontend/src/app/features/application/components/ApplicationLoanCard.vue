<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ApplicationLoanInterface } from '@/app/types/application/application-interface'

const props = defineProps<{
  loan: ApplicationLoanInterface
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatDateTime } = useFormatters()

const amount = computed(() => formatCurrency(props.loan.amount, 'RUB'))
const rate = computed(() => formatPercent(props.loan.rate))
const disbursedAt = computed(() =>
  formatDateTime(props.loan.disbursedAt, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
)
</script>

<template>
  <section class="flex flex-col gap-5">
    <div class="flex items-center gap-3">
      <span
        class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-green-500/10
               text-green-700 dark:text-green-400"
        aria-hidden="true"
      >
        <i class="pi pi-check-circle text-2xl" />
      </span>

      <div>
        <h2 class="text-lg font-bold tracking-tight text-fino-text">
          {{ t('application.loan.title') }}
        </h2>

        <p class="text-sm text-fino-text-muted">
          {{ t('application.loan.disbursedAt', { date: disbursedAt }) }}
        </p>
      </div>
    </div>

    <p class="break-words text-3xl font-bold tracking-tight text-fino-text">
      {{ amount }}
    </p>

    <dl class="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
      <div>
        <dt class="text-xs text-fino-text-muted">
          {{ t('application.offers.rate') }}
        </dt>
        <dd class="mt-0.5 font-semibold text-fino-text">
          {{ rate }}
        </dd>
      </div>

      <div>
        <dt class="text-xs text-fino-text-muted">
          {{ t('application.offers.termLabel') }}
        </dt>
        <dd class="mt-0.5 font-semibold text-fino-text">
          {{ t('application.term', loan.termMonths) }}
        </dd>
      </div>

      <div class="col-span-2 min-w-0 sm:col-span-1">
        <dt class="text-xs text-fino-text-muted">
          {{ t('application.loan.number') }}
        </dt>
        <dd class="mt-0.5 truncate font-semibold text-fino-text">
          {{ loan.loanId }}
        </dd>
      </div>
    </dl>
  </section>
</template>
