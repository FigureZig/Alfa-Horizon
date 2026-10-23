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
import { ApprovalStatusEnum } from '@/app/types/application/approval-status-enum'

const props = defineProps<{
  inn: string
  applicationId: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency } = useFormatters()
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
          class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted"
        >
          {{ company.shortName }}
        </p>

        <h1 class="mt-1 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ title }} · {{ formatCurrency(application.request.amount, 'RUB') }}
        </h1>

        <p
          v-if="myShare !== null"
          class="mt-2 text-sm text-fino-text-muted"
        >
          {{ t('votes.yourShare', { share: myShare }) }}
        </p>
      </div>

      <!-- Почему спрашивают: одна строка с нормой закона -->
      <p
        class="flex items-start gap-3 rounded-2xl border border-fino-border bg-fino-surface p-4 text-sm
               leading-relaxed text-fino-text-muted"
      >
        <i
          class="pi pi-info-circle mt-0.5 shrink-0 text-primary"
          aria-hidden="true"
        />
        {{ t('votes.why') }}
      </p>

      <div
        class="rounded-2xl border p-4 text-sm font-semibold text-fino-text"
        :class="outcomeClass"
        role="status"
      >
        {{ t(`votes.outcome.${outcome}`, { vote: myVote ? t(`application.approval.vote.${myVote}`).toLowerCase() : '' }) }}
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
