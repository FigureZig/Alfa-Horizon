<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import BankDistributionCard from '@/app/features/bank/components/BankDistributionCard.vue'
import BankMetricCard from '@/app/features/bank/components/BankMetricCard.vue'
import BankMetricsSkeleton from '@/app/features/bank/components/BankMetricsSkeleton.vue'
import BankTimingCard from '@/app/features/bank/components/BankTimingCard.vue'
import { useBankMetrics } from '@/app/composables/useBankMetrics'
import { useFormatters } from '@/app/composables/useFormatters'

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()
const {
  metrics,
  isMetricsLoading,
  metricsError,
  loadMetrics,
} = useBankMetrics()

const isSkeletonVisible = computed(() => isMetricsLoading.value && !metrics.value)

const outcomeItems = computed(() =>
  Object.entries(metrics.value?.outcomes ?? {}).map(([key, count]) => ({
    key,
    label: t(`application.outcome.${key}`),
    count,
  })),
)

const statusItems = computed(() =>
  Object.entries(metrics.value?.byStatus ?? {}).map(([key, count]) => ({
    key,
    label: t(`application.status.${key}`),
    count,
  })),
)

const stpValue = computed(() =>
  metrics.value?.stpShare === null || !metrics.value ? '—' : formatPercent(metrics.value.stpShare * 100),
)

const stpHint = computed(() =>
  metrics.value
    ? t('bank.metrics.stpHint', { auto: metrics.value.autoDecisions, manual: metrics.value.manualDecisions })
    : '',
)

const issuedHint = computed(() =>
  metrics.value ? t('bank.metrics.issuedHint', { amount: formatCurrency(metrics.value.issuedAmount, 'RUB') }) : '',
)

const isRefreshing = computed(() => isMetricsLoading.value)
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-fino-text sm:text-5xl">
          {{ t('bank.metrics.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm text-fino-text-muted">
          {{ t('bank.metrics.description') }}
        </p>
      </div>

      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-fino-surface px-4 py-2.5
               text-sm font-semibold text-fino-text hover:bg-fino-surface-hover disabled:cursor-not-allowed
               disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
               btn-key"
        :disabled="isRefreshing"
        @click="loadMetrics"
      >
        <i
          :class="isRefreshing ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'"
          class="text-xs"
          aria-hidden="true"
        />
        {{ t('bank.metrics.refresh') }}
      </button>
    </div>

    <div class="flex min-w-0 flex-col gap-6">
      <BankMetricsSkeleton v-if="isSkeletonVisible" />

      <AppErrorState
        v-else-if="metricsError"
        :message="t('bank.metrics.loadError')"
        @retry="loadMetrics"
      />

      <template v-else-if="metrics">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          <BankMetricCard
            :label="t('bank.metrics.applications')"
            :value="String(metrics.applicationsCount)"
            :hint="t('bank.metrics.applicationsHint')"
            icon="pi pi-file-edit"
          />

          <BankMetricCard
            :label="t('bank.metrics.stp')"
            :value="stpValue"
            :hint="stpHint"
            icon="pi pi-bolt"
          />

          <BankMetricCard
            :label="t('bank.metrics.issued')"
            :value="String(metrics.issuedCount)"
            :hint="issuedHint"
            icon="pi pi-check-circle"
          />

          <BankMetricCard
            :label="t('bank.metrics.slaBreaches')"
            :value="String(metrics.slaBreaches)"
            :hint="t('bank.metrics.slaHint')"
            icon="pi pi-clock"
            :is-alert="metrics.slaBreaches > 0"
          />
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <BankTimingCard
            :title="t('bank.metrics.timeToDecision')"
            :description="t('bank.metrics.timeToDecisionHint')"
            :timing="metrics.timeToDecision"
          />

          <BankTimingCard
            :title="t('bank.metrics.manualReview')"
            :description="t('bank.metrics.manualReviewHint')"
            :timing="metrics.manualReview"
          />
        </div>

        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <BankDistributionCard
            :title="t('bank.metrics.outcomes')"
            :items="outcomeItems"
          />

          <BankDistributionCard
            :title="t('bank.metrics.byStatus')"
            :items="statusItems"
          />
        </div>
      </template>
    </div>
  </div>
</template>
