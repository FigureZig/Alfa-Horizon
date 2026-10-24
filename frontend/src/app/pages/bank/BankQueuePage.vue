<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import BankQueueTable from '@/app/features/bank/components/BankQueueTable.vue'
import BankQueueCardSkeleton from '@/app/features/bank/components/BankQueueCardSkeleton.vue'
import DashboardSummarySection from '@/app/features/dashboard/components/DashboardSummarySection.vue'
import { useBankQueue } from '@/app/composables/useBankQueue'
import { useCompanyNames } from '@/app/composables/useCompanyNames'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { useWorldClock } from '@/app/composables/useWorldClock'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { BankQueueItemInterface } from '@/app/types/bank/bank-queue-item-interface'

const QUEUE_SKELETON_COUNT = 3

defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { demoPersona } = useDemoPersona()
const { queue, isLoading, error, loadQueue } = useBankQueue()
const { getCompanyName, isLoading: isNamesLoading } = useCompanyNames()
// Срок рассмотрения — отсчётом по часам мира
const { now } = useWorldClock()
const { openPanel } = useReviewerPanel()

// Задача сотрудника — заявка, по которой бэкенд отдал ему решение или подтверждение
function isMine(item: BankQueueItemInterface): boolean {
  return item.availableActions.some((action) =>
    action === ApplicationActionEnum.Decide || action === ApplicationActionEnum.Confirm)
}

function toCard(item: BankQueueItemInterface) {
  return { item, isMine: isMine(item), companyName: getCompanyName.value(item.inn) }
}

const myCards = computed(() => queue.value.filter(isMine).map(toCard))
const colleaguesCards = computed(() => queue.value.filter((item) => !isMine(item)).map(toCard))

// Карточки показываем вместе с названиями компаний, чтобы заголовок не менялся на глазах
const isSkeletonVisible = computed(() => (isLoading.value && !queue.value.length && !error.value) || isNamesLoading.value)
const isEmpty = computed(() => !isLoading.value && !isNamesLoading.value && !error.value && !queue.value.length)

// Сводка обновляется, когда меняется состав или состояние очереди
const summaryKey = computed(() =>
  queue.value.map((item) => `${item.id}:${item.status}:${item.pendingDecision ? 1 : 0}`).join('|'),
)

const roleLabel = computed(() => (demoPersona.value ? t(`bank.role.${demoPersona.value.role}`) : ''))

// Пустая очередь — тупик для проверяющего: сценарии со специалистом лежат в панели «Как проверить»
function openScenarios() {
  openPanel()
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-fino-text sm:text-5xl">
          {{ t('bank.queue.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm text-fino-text-muted">
          {{ t('bank.queue.description') }}
        </p>
      </div>

      <p
        v-if="roleLabel"
        class="inline-flex items-center gap-2 rounded-xl bg-fino-accent px-3 py-2 text-sm font-semibold text-primary"
      >
        <i
          class="pi pi-briefcase text-xs"
          aria-hidden="true"
        />
        {{ roleLabel }}
      </p>
    </div>

    <DashboardSummarySection
      :inn="inn"
      :refresh-key="summaryKey"
    />

    <div
      v-if="isSkeletonVisible"
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      aria-busy="true"
    >
      <BankQueueCardSkeleton
        v-for="index in QUEUE_SKELETON_COUNT"
        :key="index"
      />
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('bank.queue.loadError')"
      @retry="loadQueue"
    />

    <div
      v-else-if="isEmpty"
      class="flex flex-col items-center rounded-3xl border-dashed bg-fino-surface px-6 py-12 text-center border-2
             border-fino-line/40"
    >
      <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary border-2 border-fino-line">
        <i
          class="pi pi-inbox text-2xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 text-base font-semibold text-fino-text">
        {{ t('bank.queue.empty') }}
      </p>

      <p class="mt-1 max-w-sm text-sm text-fino-text-muted">
        {{ t('bank.queue.emptyHint') }}
      </p>

      <p class="mt-3 max-w-md text-sm text-fino-text-muted">
        {{ t('bank.queue.howToFill') }}
      </p>

      <div class="mt-1 flex flex-wrap items-center justify-center gap-x-4 gap-y-1">
        <button
          type="button"
          class="mt-3 inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-xl bg-fino-surface px-3.5 text-sm
                 font-semibold text-fino-text hover:bg-fino-surface-hover focus-visible:outline-2
                 focus-visible:outline-primary btn-key"
          @click="openScenarios"
        >
          <i
            class="pi pi-compass text-primary"
            aria-hidden="true"
          />
          {{ t('bank.queue.openScenarios') }}
        </button>

        <RouterLink
          :to="{ name: 'bank-metrics', params: { inn } }"
          class="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
        >
          {{ t('bank.queue.toMetrics') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </RouterLink>
      </div>
    </div>

    <template v-else>
      <section
        v-if="myCards.length"
        class="flex flex-col gap-4"
        :aria-label="t('bank.queue.mine')"
      >
        <h2 class="text-lg font-bold tracking-tight text-fino-text">
          {{ t('bank.queue.mine') }}
          <span class="text-fino-text-muted">· {{ myCards.length }}</span>
        </h2>

        <BankQueueTable
          :inn="inn"
          :rows="myCards"
          :now="now"
        />
      </section>

      <div
        v-else
        class="rounded-3xl border-dashed bg-fino-surface p-6 border-2 border-fino-line/40"
      >
        <p class="text-sm font-semibold text-fino-text">
          {{ t('bank.queue.nothingForYou') }}
        </p>

        <p class="mt-1 text-sm text-fino-text-muted">
          {{ t('bank.queue.howToFill') }}
        </p>

        <button
          type="button"
          class="mt-3 inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-xl bg-fino-surface px-3.5 text-sm
                 font-semibold text-fino-text hover:bg-fino-surface-hover focus-visible:outline-2
                 focus-visible:outline-primary btn-key"
          @click="openScenarios"
        >
          <i
            class="pi pi-compass text-primary"
            aria-hidden="true"
          />
          {{ t('bank.queue.openScenarios') }}
        </button>
      </div>

      <section
        v-if="colleaguesCards.length"
        class="flex flex-col gap-4"
        :aria-label="t('bank.queue.colleagues')"
      >
        <h2 class="text-lg font-bold tracking-tight text-fino-text">
          {{ t('bank.queue.colleagues') }}
          <span class="text-fino-text-muted">· {{ colleaguesCards.length }}</span>
        </h2>

        <BankQueueTable
          :inn="inn"
          :rows="colleaguesCards"
          :now="now"
        />
      </section>
    </template>
  </div>
</template>
