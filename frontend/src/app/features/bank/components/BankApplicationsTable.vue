<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import ApplicationStatusBadge from '@/app/features/application/components/ApplicationStatusBadge.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { BankDecidedByEnum } from '@/app/types/bank/bank-decided-by-enum'
import type { BankApplicationInterface } from '@/app/types/bank/bank-application-interface'

const RISK_TONES: Record<string, string> = {
  A: 'bg-green-500/10 text-green-700 dark:text-green-400',
  B: 'bg-green-500/10 text-green-700 dark:text-green-400',
  C: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  D: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

defineProps<{
  inn: string
  applications: BankApplicationInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { formatCurrency, formatDateTime } = useFormatters()

function getRoute(inn: string, applicationId: string) {
  return { name: 'bank-dossier', params: { inn, applicationId }, query: { from: 'applications' } }
}

function openApplication(inn: string, applicationId: string) {
  router.push(getRoute(inn, applicationId))
}

function formatUpdated(updatedAt: string) {
  return formatDateTime(updatedAt, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

function getRiskTone(riskClass: string | null) {
  return riskClass ? RISK_TONES[riskClass] ?? 'bg-fino-surface-secondary text-fino-text-muted' : ''
}

function getDecidedByLabel(decidedBy: BankDecidedByEnum | null) {
  return decidedBy ? t(`bank.applications.decidedBy.${decidedBy}`) : t('bank.applications.decidedBy.none')
}

function isDecidedByBank(decidedBy: BankDecidedByEnum | null) {
  return decidedBy === BankDecidedByEnum.Bank
}
</script>

<template>
  <div>
    <!-- Десктоп: таблица -->
    <div class="hidden overflow-hidden rounded-3xl border border-fino-border bg-fino-surface shadow-sm lg:block">
      <table class="w-full border-collapse text-left text-sm">
        <thead class="bg-fino-surface-secondary text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
          <tr>
            <th
              scope="col"
              class="px-5 py-3"
            >
              {{ t('bank.applications.columns.company') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3"
            >
              {{ t('bank.applications.columns.product') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3 text-right"
            >
              {{ t('bank.applications.columns.amount') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3"
            >
              {{ t('bank.applications.columns.status') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3"
            >
              {{ t('bank.applications.columns.decision') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3"
            >
              {{ t('bank.applications.columns.risk') }}
            </th>
            <th
              scope="col"
              class="px-5 py-3 text-right"
            >
              {{ t('bank.applications.columns.updated') }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="item in applications"
            :key="item.id"
            class="cursor-pointer border-t border-fino-border transition-colors duration-150 hover:bg-fino-surface-hover
                   motion-reduce:transition-none"
            @click="openApplication(inn, item.id)"
          >
            <td class="max-w-72 px-5 py-3.5">
              <RouterLink
                :to="getRoute(inn, item.id)"
                class="block truncate font-semibold text-fino-text hover:text-primary focus-visible:outline-2
                       focus-visible:outline-primary"
                @click.stop
              >
                {{ item.companyName ?? item.inn }}
              </RouterLink>
              <p class="mt-0.5 text-xs text-fino-text-muted">
                {{ t('bank.queue.companyInn', { inn: item.inn }) }}
              </p>
            </td>

            <td class="px-4 py-3.5 text-fino-text">
              {{ t(`application.product.${item.product}`) }}
            </td>

            <td class="px-4 py-3.5 text-right font-semibold whitespace-nowrap text-fino-text">
              {{ formatCurrency(item.amount, 'RUB') }}
            </td>

            <td class="px-4 py-3.5">
              <ApplicationStatusBadge :status="item.status" />
            </td>

            <td class="px-4 py-3.5">
              <p class="text-fino-text">
                {{ item.outcome ? t(`application.outcome.${item.outcome}`) : '—' }}
              </p>
              <p
                class="mt-0.5 text-xs"
                :class="isDecidedByBank(item.decidedBy) ? 'font-semibold text-primary' : 'text-fino-text-muted'"
              >
                {{ getDecidedByLabel(item.decidedBy) }}
              </p>
            </td>

            <td class="px-4 py-3.5">
              <span
                v-if="item.riskClass"
                class="inline-flex size-7 items-center justify-center rounded-lg text-xs font-bold"
                :class="getRiskTone(item.riskClass)"
              >
                {{ item.riskClass }}
              </span>
              <span
                v-else
                class="text-fino-text-muted"
              >—</span>
            </td>

            <td class="px-5 py-3.5 text-right text-xs whitespace-nowrap text-fino-text-muted">
              {{ formatUpdated(item.updatedAt) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Мобильный: карточки -->
    <ul class="flex flex-col gap-3 lg:hidden">
      <li
        v-for="item in applications"
        :key="item.id"
      >
        <RouterLink
          :to="getRoute(inn, item.id)"
          class="flex flex-col gap-3 rounded-2xl border border-fino-border bg-fino-surface p-4 shadow-sm
                 transition-colors hover:border-primary/40 focus-visible:outline-2 focus-visible:outline-primary
                 motion-reduce:transition-none"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="break-words text-sm font-bold text-fino-text">
                {{ item.companyName ?? item.inn }}
              </p>
              <p class="mt-0.5 text-xs text-fino-text-muted">
                {{ t(`application.product.${item.product}`) }}
              </p>
            </div>

            <ApplicationStatusBadge :status="item.status" />
          </div>

          <div class="flex items-end justify-between gap-3">
            <p class="text-lg font-bold tracking-tight text-fino-text">
              {{ formatCurrency(item.amount, 'RUB') }}
            </p>

            <p class="text-right text-xs text-fino-text-muted">
              <span :class="isDecidedByBank(item.decidedBy) ? 'font-semibold text-primary' : ''">
                {{ getDecidedByLabel(item.decidedBy) }}
              </span>
              · {{ formatUpdated(item.updatedAt) }}
            </p>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
