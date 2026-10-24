<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ApplicationVoteBar from '@/app/features/application/components/ApplicationVoteBar.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'
import type { Nullable } from '@/app/types/nullable'
import type { VoteItemInterface } from '@/app/types/application/vote-item-interface'

const props = defineProps<{
  inn: string
  item: VoteItemInterface
  // ИНН текущего человека-участника: по нему видно, голосовал ли он и какая у него доля
  personInn: Nullable<string>
  // Сегодняшняя дата мира, YYYY-MM-DD: срок считается по ней, а не по часам браузера
  today: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, getDaysLeft } = useFormatters()

const approval = computed(() => props.item.application.approval)

const productName = computed(() =>
  props.item.application.offer?.productName ?? t(`application.product.${props.item.application.request.product}`),
)

const myVote = computed(() =>
  approval.value?.votes.find((vote) => vote.inn === props.personInn)?.vote ?? null,
)

const myShare = computed(() =>
  approval.value?.participants.find((participant) => participant.inn === props.personInn)?.share ?? null,
)

const statusLabel = computed(() => {
  if (approval.value?.status === ApprovalStatusEnum.Approved) return t('votes.status.approved')
  if (approval.value?.status === ApprovalStatusEnum.Rejected) return t('votes.status.rejected')

  return myVote.value
    ? t('votes.status.voted', { vote: t(`application.approval.vote.${myVote.value}`).toLowerCase() })
    : t('votes.status.waiting')
})

const statusClass = computed(() => {
  if (approval.value?.status === ApprovalStatusEnum.Approved) return 'bg-green-500/10 text-green-700 dark:text-green-400'
  if (approval.value?.status === ApprovalStatusEnum.Rejected) return 'bg-red-500/10 text-red-700 dark:text-red-400'

  return myVote.value ? 'bg-fino-surface-secondary text-fino-text-muted' : 'bg-fino-accent text-primary'
})

// Сколько дней осталось до срока голосования
const daysLeft = computed(() => (props.today ? getDaysLeft(props.item.task.dueDate, props.today) : null))
</script>

<template>
  <RouterLink
    :to="{ name: 'vote', params: { inn, applicationId: item.application.id } }"
    class="group flex h-full min-w-0 flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-6
           shadow-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-md
           focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none
           motion-reduce:hover:translate-y-0"
  >
    <div class="flex items-start justify-between gap-3">
      <p class="min-w-0 break-words text-base font-bold tracking-tight text-fino-text">
        {{ productName }}
      </p>

      <span
        class="shrink-0 rounded-full px-3 py-1 text-xs font-semibold"
        :class="statusClass"
      >
        {{ statusLabel }}
      </span>
    </div>

    <div>
      <p class="text-3xl font-bold tracking-tight text-fino-text">
        {{ formatCurrency(item.application.request.amount, 'RUB') }}
      </p>

      <p
        v-if="myShare !== null"
        class="mt-1 text-sm text-fino-text-muted"
      >
        {{ t('votes.yourShare', { share: myShare }) }}
      </p>
    </div>

    <ApplicationVoteBar
      v-if="approval"
      :for-percent="approval.forPercent"
      :against-percent="approval.againstPercent"
      :threshold-percent="approval.thresholdPercent"
    />

    <p
      v-if="daysLeft !== null"
      class="mt-auto flex items-center gap-2 text-sm text-fino-text-muted"
    >
      <i
        class="pi pi-clock text-xs"
        aria-hidden="true"
      />
      {{ t('votes.daysLeft', daysLeft) }}
    </p>
  </RouterLink>
</template>
