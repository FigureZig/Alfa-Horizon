<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import BankQueueCard from './BankQueueCard.vue'
import BankSlaBadge from './BankSlaBadge.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'
import type { Nullable } from '@/app/types/nullable'

interface QueueRowInterface {
  item: BankQueueItemInterface
  companyName: string
  // Задача текущего сотрудника: бэкенд отдал ему действие по заявке
  isMine: boolean
}

defineProps<{
  inn: string
  rows: QueueRowInterface[]
  // «Сейчас» по часам мира — для отсчёта «осталось 3 ч 40 мин»
  now: Nullable<number>
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { formatCurrency, formatTerm } = useFormatters()

function getRoute(inn: string, applicationId: string) {
  return { name: 'bank-dossier', params: { inn, applicationId } }
}

function openApplication(inn: string, applicationId: string) {
  router.push(getRoute(inn, applicationId))
}

function getRequestText(item: BankQueueItemInterface) {
  const term = item.request.termMonths ? ` · ${formatTerm(item.request.termMonths)}` : ''

  return `${formatCurrency(item.request.amount, 'RUB')}${term}`
}

</script>

<template>
  <div>
    <!-- Десктоп: плотная таблица, строка открывает досье -->
    <div class="hidden overflow-hidden card-key lg:block">
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
              {{ t('bank.queue.columns.request') }}
            </th>
            <th
              scope="col"
              class="px-4 py-3"
            >
              {{ t('bank.queue.columns.reason') }}
            </th>
            <th
              scope="col"
              class="px-5 py-3 text-right"
            >
              {{ t('bank.queue.columns.sla') }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="row in rows"
            :key="row.item.id"
            class="cursor-pointer border-t border-fino-border transition-colors duration-150 hover:bg-fino-surface-hover
                   motion-reduce:transition-none"
            :class="row.isMine ? 'bg-fino-accent/30' : ''"
            @click="openApplication(inn, row.item.id)"
          >
            <td class="max-w-64 px-5 py-3.5">
              <RouterLink
                :to="getRoute(inn, row.item.id)"
                class="block truncate font-semibold text-fino-text hover:text-primary focus-visible:outline-2
                       focus-visible:outline-primary"
                @click.stop
              >
                {{ row.companyName || t('bank.queue.companyInn', { inn: row.item.inn }) }}
              </RouterLink>
              <p
                v-if="row.companyName"
                class="mt-0.5 text-xs text-fino-text-muted"
              >
                {{ t('bank.queue.companyInn', { inn: row.item.inn }) }}
              </p>
            </td>

            <td class="px-4 py-3.5">
              <p class="text-fino-text">
                {{ t(`application.product.${row.item.request.product}`) }}
              </p>
              <p class="mt-0.5 text-xs whitespace-nowrap text-fino-text-muted">
                {{ getRequestText(row.item) }}
              </p>
            </td>

            <td class="max-w-80 px-4 py-3.5">
              <p class="line-clamp-2 text-fino-text">
                {{ row.item.reasons[0]?.text ?? '—' }}
              </p>
              <p
                v-if="row.item.reasons.length > 1"
                class="mt-0.5 text-xs text-fino-text-muted"
              >
                {{ t('bank.queue.moreReasons', { n: row.item.reasons.length - 1 }) }}
              </p>
            </td>

            <td class="px-5 py-3.5 text-right">
              <BankSlaBadge
                :sla-until="row.item.slaUntil"
                :flags="row.item.flags"
                :now="now"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Мобильный: карточки -->
    <ul class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:hidden">
      <li
        v-for="row in rows"
        :key="row.item.id"
        class="flex"
      >
        <BankQueueCard
          class="w-full"
          :item="row.item"
          :inn="inn"
          :company-name="row.companyName"
          :is-mine="row.isMine"
          :now="now"
        />
      </li>
    </ul>
  </div>
</template>
