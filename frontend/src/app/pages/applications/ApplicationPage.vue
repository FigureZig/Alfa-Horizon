<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
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
import ApplicationWorldNotice from '@/app/features/application/components/ApplicationWorldNotice.vue'
import { useApplication } from '@/app/composables/useApplication'
import { useApplicationExplanation } from '@/app/composables/useApplicationExplanation'
import { useApplicationStatusView } from '@/app/composables/useApplicationStatusView'
import { useApplicationWorldChange } from '@/app/composables/useApplicationWorldChange'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { useCompanyProfile } from '@/app/composables/useCompanyProfile'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { Nullable } from '@/app/types/nullable'

type ConfirmKind = 'withdraw' | 'decline'

// Эти отметки объясняет шапка заявки и плашка «Данные компании изменились»
const HEADER_FLAGS: ApplicationFlagEnum[] = [
  ApplicationFlagEnum.Provisional,
  ApplicationFlagEnum.Recheck,
  ApplicationFlagEnum.SlaBreach,
  ApplicationFlagEnum.DisburseError,
]

const props = defineProps<{
  inn: string
  applicationId: string
}>()

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const { demoPersona } = useDemoPersona()
const { me } = useCompanyAccess(() => props.inn)
const { profile } = useCompanyProfile(() => props.inn)
const { formatCurrency, formatDateTime, formatShortName } = useFormatters()

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
const directors = computed(() => profile.value?.directors ?? [])

// Шапка для того, кто смотрит: текст, срок и кнопка зависят от моих прав и от того, кто ещё действует
const { view: statusView, step } = useApplicationStatusView(() =>
  application.value
    ? {
      application: application.value,
      explanation: explanation.value,
      personInn: me.value?.personInn ?? null,
      directors: directors.value,
      today: demoPersona.value?.today ?? null,
    }
    : null,
)

// Событие реестра пересмотрело заявку: объясняем, что изменилось
const { lastChange } = useApplicationWorldChange(events)
const worldChange = computed(() =>
  application.value?.flags.includes(ApplicationFlagEnum.Recheck) ? lastChange.value : null,
)
const isRecalculating = computed(() =>
  status.value === ApplicationDetailStatusEnum.Checking || status.value === ApplicationDetailStatusEnum.Submitted,
)
const directorName = computed(() => {
  const name = directors.value[0]?.fullName

  return name ? formatShortName(name) : null
})

// Сколько показывал подбор до заявки: «Почему» объяснит, если банк дал меньше
const shownAmount = computed(() => {
  const value = Number(route.query.shown)

  return Number.isFinite(value) && value > 0 ? value : null
})
const isProvisional = computed(() => Boolean(application.value?.flags.includes(ApplicationFlagEnum.Provisional)))

const extraFlags = computed(() => application.value?.flags.filter((flag) => !HEADER_FLAGS.includes(flag)) ?? [])
const isLimit = computed(() => {
  const current = application.value

  return current?.loan?.isLimit ?? (current?.offer ?? current?.offers[0])?.product === CreditProductCodeEnum.Overdraft
})

// Главную причину отказа называет шапка; остальные причины и подсказки — ниже
const extraReasons = computed(() =>
  status.value === ApplicationDetailStatusEnum.Rejected ? application.value?.decision?.reasons.slice(1) ?? [] : [],
)
const hints = computed(() =>
  status.value === ApplicationDetailStatusEnum.Rejected ? application.value?.decision?.hints ?? [] : [],
)

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


// Отзыв доступен почти на всех шагах; при оферте вместо него — «Отказаться от предложения»
const canWithdraw = computed(() =>
  hasAction(ApplicationActionEnum.Withdraw)
  && status.value !== ApplicationDetailStatusEnum.Offered,
)

// Карточка с содержимым шага: предложения, ответ банку, подписанты, договор, остальные причины отказа
const hasMainPanel = computed(() => {
  switch (status.value) {
    case ApplicationDetailStatusEnum.Offered:
    case ApplicationDetailStatusEnum.InfoRequested:
    case ApplicationDetailStatusEnum.Signing:
      return true
    case ApplicationDetailStatusEnum.Issued:
      return Boolean(application.value?.loan)
    default:
      return extraReasons.value.length > 0 || hints.value.length > 0
  }
})

const confirmTitle = computed(() => (confirmKind.value ? t(`application.confirm.${confirmKind.value}.title`) : ''))
const confirmText = computed(() => (confirmKind.value ? t(`application.confirm.${confirmKind.value}.text`) : ''))

// Главная кнопка шапки: подать черновик или открыть «Проверьте условия» перед подписью
function handleCommand(action: ApplicationActionEnum) {
  if (action === ApplicationActionEnum.Submit) {
    submit()
  } else if (action === ApplicationActionEnum.Sign) {
    isSignVisible.value = true
  }
}

function handleAccept(variant: number) {
  acceptOffer(variant)
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
          :flags="extraFlags"
        />
      </div>

      <!-- Что происходит для меня, кто действует и сколько осталось -->
      <ApplicationHero
        v-if="statusView"
        :view="statusView"
        :step="step"
        :pending-action="pendingAction"
        :can-withdraw="canWithdraw"
        @command="handleCommand"
        @withdraw="askWithdraw"
      />

      <ApplicationWorldNotice
        v-if="worldChange"
        :change="worldChange"
        :is-recalculating="isRecalculating"
        :director-name="directorName"
      />

      <div
        class="grid grid-cols-1 items-start gap-6"
        :class="hasMainPanel ? 'xl:grid-cols-[minmax(0,1fr)_24rem]' : application.decision ? 'xl:grid-cols-2' : ''"
      >
        <div
          v-if="hasMainPanel"
          class="flex min-w-0 flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6"
        >
          <!-- Содержимое шага; кнопки — только те, что вернул бэкенд -->
          <ApplicationOffersPanel
            v-if="status === ApplicationDetailStatusEnum.Offered"
            :offers="application.offers"
            :request="application.request"
            :decision="application.decision"
            :can-accept="hasAction(ApplicationActionEnum.AcceptOffer)"
            :can-decline="hasAction(ApplicationActionEnum.DeclineOffer)"
            :pending-action="pendingAction"
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
            :directors="directors"
          />

          <ApplicationLoanCard
            v-else-if="status === ApplicationDetailStatusEnum.Issued && application.loan"
            :loan="application.loan"
          />

          <ApplicationStatusPanel
            v-else
            :reasons="extraReasons"
            :hints="hints"
          />
        </div>

        <ApplicationExplanationCard
          v-if="application.decision && !hasMainPanel"
          :explanation="explanation"
          :is-loading="isExplanationLoading"
          :has-error="explanationError"
          :requested-amount="application.request.amount"
          :shown-amount="shownAmount"
          :is-provisional="isProvisional"
          :sources="profile?.sources ?? []"
          @retry="loadExplanation"
        />

        <aside
          v-if="hasMainPanel"
          class="flex min-w-0 flex-col gap-6"
        >
          <ApplicationExplanationCard
            v-if="application.decision"
            :explanation="explanation"
            :is-loading="isExplanationLoading"
            :has-error="explanationError"
            :requested-amount="application.request.amount"
            :shown-amount="shownAmount"
            :is-provisional="isProvisional"
            :sources="profile?.sources ?? []"
            @retry="loadExplanation"
          />

          <div class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm">
            <ApplicationTimeline
              :events="events"
              :is-limit="isLimit"
            />
          </div>
        </aside>

        <div
          v-else
          class="min-w-0 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
        >
          <ApplicationTimeline
            :events="events"
            :is-limit="isLimit"
          />
        </div>
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
