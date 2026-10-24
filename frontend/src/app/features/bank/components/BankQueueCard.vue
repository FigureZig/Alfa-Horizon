<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import BankSlaBadge from './BankSlaBadge.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  item: BankQueueItemInterface
  inn: string
  companyName: string
  // Задача текущего сотрудника: бэкенд отдал ему действие по заявке
  isMine: boolean
  // «Сейчас» по часам мира — для отсчёта срока
  now: Nullable<number>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatTerm } = useFormatters()

const route = computed(() => ({ name: 'bank-dossier', params: { inn: props.inn, applicationId: props.item.id } }))

const title = computed(() => props.companyName || t('bank.queue.companyInn', { inn: props.item.inn }))
const subtitle = computed(() => (props.companyName ? t('bank.queue.companyInn', { inn: props.item.inn }) : ''))

const request = computed(() => {
  const { request: current } = props.item
  const term = current.termMonths ? ` · ${formatTerm(current.termMonths)}` : ''

  return `${t(`application.product.${current.product}`)} · ${formatCurrency(current.amount, 'RUB')}${term}`
})

const reasons = computed(() => props.item.reasons.map((reason) => reason.text))

const isWaitingSecondKey = computed(() => Boolean(props.item.pendingDecision))
</script>

<template>
  <RouterLink
    :to="route"
    class="group flex min-w-0 flex-col gap-4 p-5 transition-transform duration-200 hover:-translate-y-1
           focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none
           motion-reduce:hover:translate-y-0 card-key"
    :class="isMine ? 'bg-fino-accent' : ''"
  >
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="break-words text-base font-bold tracking-tight text-fino-text">
          {{ title }}
        </p>

        <p
          v-if="subtitle"
          class="mt-0.5 text-xs text-fino-text-muted"
        >
          {{ subtitle }}
        </p>
      </div>

      <BankSlaBadge
        :sla-until="item.slaUntil"
        :flags="item.flags"
        :now="now"
      />
    </div>

    <div>
      <p class="break-words text-sm font-semibold text-fino-text">
        {{ request }}
      </p>
    </div>

    <ul
      v-if="reasons.length"
      class="flex flex-col gap-1.5"
    >
      <li
        v-for="reason in reasons"
        :key="reason"
        class="flex items-start gap-2 rounded-xl bg-fino-accent px-3 py-2 text-xs text-fino-text"
      >
        <i
          class="pi pi-exclamation-circle mt-0.5 text-primary"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ reason }}</span>
      </li>
    </ul>

    <div class="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-fino-border pt-3">
      <div class="flex flex-wrap items-center gap-2 text-xs text-fino-text-muted">
        <span
          v-if="item.score !== null"
          class="rounded-md bg-fino-surface-secondary px-2 py-0.5 font-semibold text-fino-text"
        >
          {{ t('bank.queue.score', { score: item.score, riskClass: item.riskClass }) }}
        </span>

        <span
          v-if="isWaitingSecondKey"
          class="inline-flex items-center gap-1 font-semibold text-primary"
        >
          <i
            class="pi pi-key text-xs"
            aria-hidden="true"
          />
          {{ t('bank.queue.waitingSecondKey') }}
        </span>
      </div>

      <span class="inline-flex items-center gap-1 text-sm font-semibold text-primary">
        {{ t('bank.queue.open') }}
        <i
          class="pi pi-arrow-right text-xs transition-transform duration-200 group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </span>
    </div>
  </RouterLink>
</template>
