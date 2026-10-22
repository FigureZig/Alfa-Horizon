<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import type { ApplicationApprovalInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  approval: ApplicationApprovalInterface
  canVote: boolean
  pendingAction: Nullable<ApplicationActionEnum>
}>()

const emit = defineEmits<{
  vote: [choice: ApplicationVoteEnum]
}>()

const { t } = useI18n({ useScope: 'global' })

const isBusy = computed(() => props.pendingAction !== null)

const participants = computed(() =>
  props.approval.participants.map((participant) => {
    const vote = props.approval.votes.find((item) => item.inn === participant.inn)?.vote

    return {
      inn: participant.inn,
      fio: participant.fio,
      share: t('application.approval.share', { share: participant.share }),
      voteLabel: vote ? t(`application.approval.vote.${vote}`) : t('application.approval.notVoted'),
      voteClass: vote === ApplicationVoteEnum.For
        ? 'text-green-700 dark:text-green-400'
        : vote === ApplicationVoteEnum.Against
          ? 'text-red-700 dark:text-red-400'
          : 'text-fino-text-muted',
    }
  }),
)

const forWidth = computed(() => ({ width: `${Math.min(props.approval.forPercent, 100)}%` }))
const againstWidth = computed(() => ({ width: `${Math.min(props.approval.againstPercent, 100)}%` }))

function handleVoteFor() {
  emit('vote', ApplicationVoteEnum.For)
}

function handleVoteAgainst() {
  emit('vote', ApplicationVoteEnum.Against)
}
</script>

<template>
  <section
    class="flex flex-col gap-4 rounded-2xl border border-fino-border p-4"
    :aria-label="t('application.approval.title')"
  >
    <div>
      <h3 class="text-sm font-bold text-fino-text">
        {{ t('application.approval.title') }}
      </h3>

      <p class="mt-1 text-xs leading-relaxed text-fino-text-muted">
        {{ t('application.approval.description', { threshold: approval.thresholdPercent }) }}
      </p>
    </div>

    <div>
      <div class="flex h-2 overflow-hidden rounded-full bg-fino-surface-secondary">
        <div
          class="bg-green-500 transition-all duration-300 motion-reduce:transition-none"
          :style="forWidth"
        />
        <div
          class="bg-red-500 transition-all duration-300 motion-reduce:transition-none"
          :style="againstWidth"
        />
      </div>

      <p class="mt-2 flex justify-between text-xs text-fino-text-muted">
        <span>{{ t('application.approval.forPercent', { percent: approval.forPercent }) }}</span>
        <span>{{ t('application.approval.againstPercent', { percent: approval.againstPercent }) }}</span>
      </p>
    </div>

    <ul class="flex flex-col divide-y divide-fino-border">
      <li
        v-for="participant in participants"
        :key="participant.inn"
        class="flex items-center justify-between gap-3 py-2 text-sm"
      >
        <span class="min-w-0 break-words text-fino-text">
          {{ participant.fio }}
          <span class="text-xs text-fino-text-muted">· {{ participant.share }}</span>
        </span>

        <span
          class="shrink-0 text-xs font-semibold"
          :class="participant.voteClass"
        >
          {{ participant.voteLabel }}
        </span>
      </li>
    </ul>

    <div
      v-if="canVote"
      class="grid grid-cols-2 gap-3"
    >
      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl
               bg-primary px-4 py-2.5 text-sm font-semibold text-primary-contrast
               transition-all duration-200 hover:opacity-90 active:scale-95
               disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isBusy"
        @click="handleVoteFor"
      >
        <i
          class="pi pi-check text-xs"
          aria-hidden="true"
        />
        {{ t('application.approval.voteFor') }}
      </button>

      <button
        type="button"
        class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl
               border border-fino-border bg-fino-surface px-4 py-2.5 text-sm font-semibold text-fino-text
               transition-colors duration-200 hover:bg-fino-surface-hover
               disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isBusy"
        @click="handleVoteAgainst"
      >
        <i
          class="pi pi-times text-xs"
          aria-hidden="true"
        />
        {{ t('application.approval.voteAgainst') }}
      </button>
    </div>
  </section>
</template>
