<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationApprovalPanel from '@/app/features/application/components/ApplicationApprovalPanel.vue'
import ApplicationPageSkeleton from '@/app/features/application/components/ApplicationPageSkeleton.vue'
import { useApplication } from '@/app/composables/useApplication'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'

const props = defineProps<{
  inn: string
  applicationId: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDateTime, formatList, formatPercent, formatShortName } = useFormatters()
const { me, company } = useCompanyAccess(() => props.inn)
const { application, isLoading, error, isNotFound, pendingAction, hasAction, loadApplication, vote } =
  useApplication(() => props.applicationId)

const approval = computed(() => application.value?.approval ?? null)

const title = computed(() => {
  const current = application.value

  if (!current) return ''

  return current.offer?.productName ?? t(`application.product.${current.request.product}`)
})

const myVote = computed(() =>
  approval.value?.votes.find((item) => item.inn === me.value?.personInn)?.vote ?? null,
)

const myShare = computed(() =>
  approval.value?.participants.find((participant) => participant.inn === me.value?.personInn)?.share ?? null,
)

const canVote = computed(() => hasAction(ApplicationActionEnum.Vote))

// Что с голосованием сейчас: ждём, согласовано или нет
const outcome = computed(() => {
  if (approval.value?.status === ApprovalStatusEnum.Approved) return 'approved'
  if (approval.value?.status === ApprovalStatusEnum.Rejected) return 'rejected'

  return myVote.value ? 'voted' : 'waiting'
})

const outcomeClass = computed(() => {
  switch (outcome.value) {
    case 'approved':
      return 'border-green-500/30 bg-green-500/5'
    case 'rejected':
      return 'border-red-500/30 bg-red-500/5'
    default:
      return 'border-fino-border bg-fino-surface-secondary'
  }
})

// «Вы за. Нужно ещё 16 %»: сделку согласуют, когда «за» больше порога
const outcomeText = computed(() => {
  const current = approval.value

  if (outcome.value === 'approved' || outcome.value === 'rejected') return t(`votes.outcome.${outcome.value}`)

  if (outcome.value === 'waiting') {
    const deadline = application.value?.deadline

    return deadline
      ? t('votes.outcome.waiting', { date: formatDateTime(deadline.at, { day: 'numeric', month: 'long' }) })
      : t('votes.outcome.waitingNoDate')
  }

  if (myVote.value === ApplicationVoteEnum.Against || !current) return t('votes.outcome.votedAgainst')

  const needed = Math.max(Math.floor(current.thresholdPercent - current.forPercent) + 1, 1)

  return t('votes.outcome.votedFor', { needed: formatPercent(needed) })
})

// Кто ещё не голосовал — после своего голоса это главное, чего ждать
const notVotedText = computed(() => {
  const current = approval.value

  if (outcome.value !== 'voted' || !current) return ''

  const votedInns = current.votes.map((item) => item.inn)
  const names = current.participants
    .filter((participant) => !votedInns.includes(participant.inn))
    .map((participant) => formatShortName(participant.fio))

  return names.length ? t('votes.outcome.notVoted', { names: formatList(names) }) : ''
})
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <RouterLink
      :to="{ name: 'votes', params: { inn } }"
      class="inline-flex w-fit items-center gap-2 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
    >
      <i
        class="pi pi-arrow-left text-xs"
        aria-hidden="true"
      />
      {{ t('votes.back') }}
    </RouterLink>

    <ApplicationPageSkeleton v-if="isLoading && !application" />

    <AppErrorState
      v-else-if="error || isNotFound || !application"
      :message="isNotFound ? t('votes.notFound') : t('votes.loadError')"
      @retry="loadApplication"
    />

    <template v-else>
      <div>
        <p
          v-if="company"
          class="text-sm font-semibold text-fino-text-muted"
        >
          {{ company.shortName }}
        </p>

        <h1 class="mt-1 text-3xl font-black text-fino-text sm:text-5xl">
          {{ title }} · {{ formatCurrency(application.request.amount, 'RUB') }}
        </h1>

        <p
          v-if="myShare !== null"
          class="mt-2 text-sm text-fino-text-muted"
        >
          {{ t('votes.yourShare', { share: myShare }) }}
        </p>
      </div>

      <!-- Почему спрашивают — одной строкой; норма закона — во всплывающей «i» -->
      <p
        class="flex items-start gap-3 rounded-2xl border border-fino-border bg-fino-surface p-4 text-sm
               leading-relaxed text-fino-text-muted"
      >
        <i
          class="pi pi-info-circle mt-0.5 shrink-0 text-primary"
          :title="t('votes.whyLaw')"
          :aria-label="t('votes.whyLaw')"
        />
        {{ t('votes.why') }}
      </p>

      <div
        class="rounded-2xl border p-4 text-sm text-fino-text"
        :class="outcomeClass"
        role="status"
      >
        <p class="font-semibold">
          {{ outcomeText }}
        </p>

        <p
          v-if="notVotedText"
          class="mt-1 text-fino-text-muted"
        >
          {{ notVotedText }}
        </p>
      </div>

      <div class="max-w-2xl">
        <ApplicationApprovalPanel
          v-if="approval"
          :approval="approval"
          :can-vote="canVote"
          :pending-action="pendingAction"
          @vote="vote"
        />
      </div>
    </template>
  </div>
</template>
