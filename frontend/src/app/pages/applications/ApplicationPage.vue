<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationExplanationCard from '@/app/features/application/components/ApplicationExplanationCard.vue'
import ApplicationHero from '@/app/features/application/components/ApplicationHero.vue'
import ApplicationFlags from '@/app/features/application/components/ApplicationFlags.vue'
import ApplicationInfoRequestPanel from '@/app/features/application/components/ApplicationInfoRequestPanel.vue'
import ApplicationLoanCard from '@/app/features/application/components/ApplicationLoanCard.vue'
import ApplicationOffersPanel from '@/app/features/application/components/ApplicationOffersPanel.vue'
import ApplicationPageSkeleton from '@/app/features/application/components/ApplicationPageSkeleton.vue'
import ApplicationSignDialog from '@/app/features/application/components/ApplicationSignDialog.vue'
import ApplicationSigningPanel from '@/app/features/application/components/ApplicationSigningPanel.vue'
import ApplicationStatusPanel from '@/app/features/application/components/ApplicationStatusPanel.vue'
import ApplicationTimeline from '@/app/features/application/components/ApplicationTimeline.vue'
import { useApplication } from '@/app/composables/useApplication'
import { useApplicationExplanation } from '@/app/composables/useApplicationExplanation'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { Nullable } from '@/app/types/nullable'

type ConfirmKind = 'withdraw' | 'decline'

const RESTART_STATUSES: ApplicationDetailStatusEnum[] = [
  ApplicationDetailStatusEnum.Rejected,
  ApplicationDetailStatusEnum.Declined,
  ApplicationDetailStatusEnum.Withdrawn,
  ApplicationDetailStatusEnum.Expired,
]

const props = defineProps<{
  inn: string
  applicationId: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { demoPersona } = useDemoPersona()
const { formatCurrency, formatDateTime } = useFormatters()

const {
  application,
  events,
  isLoading,
  error,
  isNotFound,
  pendingAction,
  hasAction,
  loadApplication,
  submit,
  withdraw,
  acceptOffer,
  declineOffer,
  sign,
  answerInfo,
  vote,
} = useApplication(() => props.applicationId)

// Объяснение решения грузим, когда решение есть, и обновляем при смене статуса
const explanationKey = computed(() => (application.value?.decision ? application.value.status : null))
const {
  explanation,
  isLoading: isExplanationLoading,
  error: explanationError,
  loadExplanation,
} = useApplicationExplanation(() => props.applicationId, explanationKey)

const confirmKind = ref<Nullable<ConfirmKind>>(null)
const isSignVisible = ref(false)

const isConfirmVisible = computed({
  get: () => confirmKind.value !== null,
  set: (isVisible: boolean) => {
    if (!isVisible) {
      confirmKind.value = null
    }
  },
})

const status = computed(() => application.value?.status ?? null)

// Условия, которые человек подписывает: принятое предложение
const signOffer = computed(() => application.value?.offer ?? application.value?.offers[0] ?? null)

const title = computed(() => {
  const current = application.value

  if (!current) return ''

  return current.offer?.productName ?? t(`application.product.${current.request.product}`)
})

const amount = computed(() => {
  const current = application.value

  return current ? formatCurrency(current.offer?.amount ?? current.request.amount, 'RUB') : ''
})

const createdAt = computed(() =>
  application.value
    ? formatDateTime(application.value.createdAt, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
    : '',
)

const deadlineAt = computed(() => application.value?.deadline?.at ?? null)

const isBusy = computed(() => pendingAction.value !== null)
const isSubmitting = computed(() => pendingAction.value === ApplicationActionEnum.Submit)
const isRestartVisible = computed(() => Boolean(status.value && RESTART_STATUSES.includes(status.value)))

// Отзыв доступен почти на всех шагах; на черновике и при оферте у него свои кнопки
const isWithdrawVisible = computed(() =>
  hasAction(ApplicationActionEnum.Withdraw)
  && status.value !== ApplicationDetailStatusEnum.Offered,
)

const confirmTitle = computed(() => (confirmKind.value ? t(`application.confirm.${confirmKind.value}.title`) : ''))
const confirmText = computed(() => (confirmKind.value ? t(`application.confirm.${confirmKind.value}.text`) : ''))

function handleSubmit() {
  submit()
}

function handleAccept(variant: number) {
  acceptOffer(variant)
}

// Подпись в два шага: сначала «Проверьте условия», потом сама подпись
function handleSign() {
  isSignVisible.value = true
}

function handleSignVisibleChange(visible: boolean) {
  isSignVisible.value = visible
}

async function confirmSign() {
  await sign()

  isSignVisible.value = false
}

function askWithdraw() {
  confirmKind.value = 'withdraw'
}

function askDecline() {
  confirmKind.value = 'decline'
}

function cancelConfirm() {
  confirmKind.value = null
}

async function confirmAction() {
  const kind = confirmKind.value

  confirmKind.value = null

  if (kind === 'withdraw') {
    await withdraw()
  } else if (kind === 'decline') {
    await declineOffer()
  }
}
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <ApplicationPageSkeleton v-if="isLoading && !application" />

    <div
      v-else-if="isNotFound"
      class="flex flex-col items-center rounded-3xl border border-dashed border-fino-border
             bg-fino-surface px-6 py-12 text-center"
    >
      <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-search text-2xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 text-base font-semibold text-fino-text">
        {{ t('application.notFound') }}
      </p>

      <RouterLink
        :to="{ name: 'applications', params: { inn } }"
        class="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        {{ t('application.back') }}
      </RouterLink>
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('application.detailLoadError')"
      @retry="loadApplication"
    />

    <template v-else-if="application && status">
      <!-- Заголовок -->
      <div>
        <RouterLink
          :to="{ name: 'applications', params: { inn } }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('application.back') }}
        </RouterLink>

        <div class="mt-3 min-w-0">
          <h1 class="break-words text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
            {{ title }}
          </h1>

          <p class="mt-1 text-sm text-fino-text-muted">
            {{ amount }} · {{ t('application.createdAt', { date: createdAt }) }}
          </p>
        </div>

        <ApplicationFlags
          class="mt-3"
          :flags="application.flags"
        />
      </div>

      <!-- Где заявка, кто сейчас действует и сколько осталось -->
      <ApplicationHero
        :application="application"
        :today="demoPersona?.today ?? null"
      />

      <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div class="flex min-w-0 flex-col gap-6">
          <div class="flex min-w-0 flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
            <!-- Содержимое зависит от статуса; кнопки — только те, что вернул бэкенд -->
            <ApplicationOffersPanel
              v-if="status === ApplicationDetailStatusEnum.Offered"
              :offers="application.offers"
              :request="application.request"
              :decision="application.decision"
              :can-accept="hasAction(ApplicationActionEnum.AcceptOffer)"
              :can-decline="hasAction(ApplicationActionEnum.DeclineOffer)"
              :pending-action="pendingAction"
              :deadline-at="deadlineAt"
              @accept="handleAccept"
              @decline="askDecline"
            />

            <ApplicationInfoRequestPanel
              v-else-if="status === ApplicationDetailStatusEnum.InfoRequested"
              :info-request="application.infoRequest"
              :approval="application.approval"
              :can-answer="hasAction(ApplicationActionEnum.AnswerInfo)"
              :can-vote="hasAction(ApplicationActionEnum.Vote)"
              :pending-action="pendingAction"
              @answer="answerInfo"
              @vote="vote"
            />

            <ApplicationSigningPanel
              v-else-if="status === ApplicationDetailStatusEnum.Signing"
              :signers="application.signers"
              :signatures="application.signatures"
              :flags="application.flags"
              :can-sign="hasAction(ApplicationActionEnum.Sign)"
              :pending-action="pendingAction"
              :deadline-at="deadlineAt"
              @sign="handleSign"
            />

            <ApplicationLoanCard
              v-else-if="status === ApplicationDetailStatusEnum.Issued && application.loan"
              :loan="application.loan"
            />

            <ApplicationStatusPanel
              v-else
              :status="status"
              :decision="application.decision"
              :sla-until="application.slaUntil"
            >
              <!-- Черновик: подать или отозвать -->
              <div
                v-if="hasAction(ApplicationActionEnum.Submit)"
                class="flex flex-col gap-3 sm:flex-row"
              >
                <button
                  type="button"
                  class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl
                         bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast
                         transition-all duration-200 hover:opacity-90 active:scale-95
                         disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                         focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                  :disabled="isBusy"
                  :aria-busy="isSubmitting"
                  @click="handleSubmit"
                >
                  <i
                    :class="isSubmitting ? 'pi pi-spinner pi-spin' : 'pi pi-send'"
                    class="text-xs"
                    aria-hidden="true"
                  />
                  {{ t('application.actions.submit') }}
                </button>
              </div>

              <!-- Заявка закрыта: можно начать заново -->
              <div
                v-if="isRestartVisible"
                class="flex flex-wrap gap-4"
              >
                <RouterLink
                  :to="{ name: 'application-new', params: { inn } }"
                  class="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
                >
                  {{ t('application.actions.newApplication') }}
                  <i
                    class="pi pi-arrow-right text-xs"
                    aria-hidden="true"
                  />
                </RouterLink>

                <RouterLink
                  :to="{ name: 'credits', params: { inn } }"
                  class="inline-flex items-center gap-1 text-sm font-semibold text-fino-text-muted transition-colors hover:text-primary"
                >
                  {{ t('application.findCredit') }}
                </RouterLink>
              </div>
            </ApplicationStatusPanel>

            <div
              v-if="isWithdrawVisible"
              class="border-t border-fino-border pt-4"
            >
              <button
                type="button"
                class="cursor-pointer text-sm font-semibold text-fino-text-muted transition-colors
                       hover:text-primary disabled:cursor-not-allowed disabled:opacity-60
                       focus-visible:outline-2 focus-visible:outline-primary"
                :disabled="isBusy"
                @click="askWithdraw"
              >
                {{ t('application.actions.withdraw') }}
              </button>
            </div>
          </div>
        </div>

        <aside class="flex min-w-0 flex-col gap-6">
          <ApplicationExplanationCard
            v-if="application.decision"
            :explanation="explanation"
            :is-loading="isExplanationLoading"
            :has-error="explanationError"
            @retry="loadExplanation"
          />

          <div class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm">
            <ApplicationTimeline :events="events" />
          </div>
        </aside>
      </div>

      <ApplicationSignDialog
        v-if="signOffer"
        :visible="isSignVisible"
        :offer="signOffer"
        :is-submitting="pendingAction === ApplicationActionEnum.Sign"
        @update:visible="handleSignVisibleChange"
        @confirm="confirmSign"
      />

      <Dialog
        v-model:visible="isConfirmVisible"
        modal
        :header="confirmTitle"
        :style="{ width: '26rem', maxWidth: '92vw' }"
      >
        <p class="text-sm leading-relaxed text-fino-text-muted">
          {{ confirmText }}
        </p>

        <template #footer>
          <button
            type="button"
            class="cursor-pointer rounded-xl border border-fino-border px-4 py-2 text-sm font-semibold
                   text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
            @click="cancelConfirm"
          >
            {{ t('application.confirm.cancel') }}
          </button>

          <button
            type="button"
            class="cursor-pointer rounded-xl bg-primary px-4 py-2 text-sm font-semibold
                   text-primary-contrast transition-opacity hover:opacity-90 motion-reduce:transition-none"
            @click="confirmAction"
          >
            {{ t('application.confirm.confirm') }}
          </button>
        </template>
      </Dialog>
    </template>
  </div>
</template>
