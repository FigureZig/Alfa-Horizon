<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import BankFactsCardSkeleton from './BankFactsCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankDossierInterface } from '@/app/types/bank/bank-dossier-interface'
import type { Nullable } from '@/app/types/nullable'

const OK_STATUS = 'ok'

const props = defineProps<{
  dossier: Nullable<BankDossierInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t, te } = useI18n({ useScope: 'global' })
const { formatAge, formatCurrency, formatPercent, formatDate, formatDateTime } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.dossier)

// Источников много: по умолчанию — сводка, а список раскрывается, и сразу, если есть проблемные
const isSourcesExpanded = ref(false)

function valueOrDash(value: Nullable<number>, format: (item: number) => string): string {
  return value === null ? t('bank.facts.noData') : format(value)
}

const companyRows = computed(() => {
  const facts = props.dossier?.facts

  if (!facts) return []

  return [
    { key: 'legalForm', label: t('bank.facts.legalForm'), value: facts.segment ? t(`companyInsights.legalForm.${facts.segment}`) : t('bank.facts.noData') },
    {
      key: 'registered',
      label: t('bank.facts.registered'),
      value: facts.registeredAt
        ? formatDate(facts.registeredAt, { day: 'numeric', month: 'long', year: 'numeric' })
        : t('bank.facts.noData'),
    },
    { key: 'age', label: t('bank.facts.age'), value: valueOrDash(facts.ageMonths, formatAge) },
    {
      key: 'okved',
      label: t('bank.facts.okved'),
      value: facts.okved ? [facts.okved, facts.okvedName].filter(Boolean).join(' · ') : t('bank.facts.noData'),
    },
    { key: 'tax', label: t('bank.facts.taxRegime'), value: facts.taxRegime ? t(`companyInsights.taxRegime.${facts.taxRegime}`) : t('bank.facts.noData') },
    { key: 'headcount', label: t('bank.facts.headcount'), value: valueOrDash(facts.headcount, String) },
  ]
})

const financeRows = computed(() => {
  const facts = props.dossier?.facts

  if (!facts) return []

  return [
    { key: 'inflow', label: t('bank.facts.monthlyInflow'), value: valueOrDash(facts.monthlyInflow, (value) => formatCurrency(value, 'RUB')) },
    { key: 'variation', label: t('bank.facts.inflowVariation'), value: valueOrDash(facts.inflowVariation, (value) => formatPercent(value * 100)) },
    { key: 'debt', label: t('bank.facts.debtLoad'), value: valueOrDash(facts.debtLoad, (value) => formatPercent(value * 100)) },
    { key: 'overdue', label: t('bank.facts.maxOverdue'), value: valueOrDash(facts.maxOverdueDays, (value) => t('credits.score.unit.days', { value })) },
    { key: 'requests', label: t('bank.facts.bkiRequests'), value: valueOrDash(facts.bkiRequests, String) },
    { key: 'taxDebt', label: t('bank.facts.taxDebt'), value: valueOrDash(facts.taxDebt, (value) => formatCurrency(value, 'RUB')) },
  ]
})

const sources = computed(() =>
  (props.dossier?.sources ?? []).map((source) => ({
    key: source.source,
    label: te(`bank.sources.${source.source}`) ? t(`bank.sources.${source.source}`) : source.source,
    isOk: source.status === OK_STATUS && !source.isStale,
    statusText: source.isStale ? t('bank.facts.stale') : source.status === OK_STATUS ? t('bank.facts.sourceOk') : t('bank.facts.sourceFailed'),
    fetchedAt: formatDateTime(source.fetchedAt, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }),
  })),
)

const problemSourcesCount = computed(() => sources.value.filter((source) => !source.isOk).length)

const sourcesSummary = computed(() =>
  problemSourcesCount.value
    ? t('bank.facts.sourcesProblems', { problems: problemSourcesCount.value, total: sources.value.length })
    : t('bank.facts.sourcesAllOk', { total: sources.value.length }),
)

const isSourcesListVisible = computed(() => isSourcesExpanded.value || problemSourcesCount.value > 0)

function toggleSources() {
  isSourcesExpanded.value = !isSourcesExpanded.value
}

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-5 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
    :aria-label="t('bank.facts.title')"
  >
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('bank.facts.title') }}
    </h2>

    <BankFactsCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('bank.facts.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <template v-else-if="dossier">
      <dl class="flex flex-col gap-1.5 text-sm">
        <div
          v-for="row in companyRows"
          :key="row.key"
          class="flex justify-between gap-3"
        >
          <dt class="shrink-0 text-fino-text-muted">
            {{ row.label }}
          </dt>
          <dd class="min-w-0 break-words text-right font-semibold text-fino-text">
            {{ row.value }}
          </dd>
        </div>
      </dl>

      <div>
        <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ t('bank.facts.finance') }}
        </h3>

        <dl class="mt-2 flex flex-col gap-1.5 text-sm">
          <div
            v-for="row in financeRows"
            :key="row.key"
            class="flex justify-between gap-3"
          >
            <dt class="shrink-0 text-fino-text-muted">
              {{ row.label }}
            </dt>
            <dd class="min-w-0 break-words text-right font-semibold text-fino-text">
              {{ row.value }}
            </dd>
          </div>
        </dl>

        <p
          v-if="!dossier.facts.isBkiKnown"
          class="mt-3 flex items-start gap-2 rounded-xl bg-fino-surface-secondary p-3 text-xs text-fino-text-muted"
        >
          <i
            class="pi pi-info-circle mt-0.5"
            aria-hidden="true"
          />
          {{ t('bank.facts.noBki') }}
        </p>
      </div>

      <div v-if="sources.length">
        <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          {{ t('bank.facts.sources') }}
        </h3>

        <div class="mt-2 flex items-center justify-between gap-3 text-sm">
          <p
            class="flex min-w-0 items-center gap-2"
            :class="problemSourcesCount ? 'font-semibold text-red-700 dark:text-red-400' : 'text-fino-text'"
          >
            <i
              :class="problemSourcesCount ? 'pi pi-exclamation-triangle' : 'pi pi-check-circle text-green-600 dark:text-green-400'"
              aria-hidden="true"
            />
            <span class="min-w-0 break-words">{{ sourcesSummary }}</span>
          </p>

          <button
            type="button"
            class="shrink-0 cursor-pointer text-xs font-semibold text-primary transition-opacity hover:opacity-80
                   focus-visible:outline-2 focus-visible:outline-primary"
            :aria-expanded="isSourcesListVisible"
            @click="toggleSources"
          >
            {{ isSourcesListVisible ? t('bank.facts.hideSources') : t('bank.facts.showSources') }}
          </button>
        </div>

        <ul
          v-if="isSourcesListVisible"
          class="mt-3 flex flex-col divide-y divide-fino-border"
        >
          <li
            v-for="source in sources"
            :key="source.key"
            class="flex items-center justify-between gap-3 py-2 text-sm first:pt-0 last:pb-0"
          >
            <span class="min-w-0 break-words text-fino-text">{{ source.label }}</span>

            <span
              class="flex shrink-0 items-center gap-1.5 text-xs"
              :class="source.isOk ? 'text-fino-text-muted' : 'font-semibold text-red-700 dark:text-red-400'"
            >
              <i
                :class="source.isOk ? 'pi pi-check-circle text-green-600 dark:text-green-400' : 'pi pi-exclamation-triangle'"
                aria-hidden="true"
              />
              {{ source.statusText }} · {{ source.fetchedAt }}
            </span>
          </li>
        </ul>
      </div>
    </template>
  </article>
</template>
