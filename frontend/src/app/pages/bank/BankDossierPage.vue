<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationExplanationCard from '@/app/features/application/components/ApplicationExplanationCard.vue'
import ApplicationFlags from '@/app/features/application/components/ApplicationFlags.vue'
import ApplicationPageSkeleton from '@/app/features/application/components/ApplicationPageSkeleton.vue'
import ApplicationStatusBadge from '@/app/features/application/components/ApplicationStatusBadge.vue'
import ApplicationTimeline from '@/app/features/application/components/ApplicationTimeline.vue'
import BankConfirmPanel from '@/app/features/bank/components/BankConfirmPanel.vue'
import BankDecisionNote from '@/app/features/bank/components/BankDecisionNote.vue'
import BankDecisionPanel from '@/app/features/bank/components/BankDecisionPanel.vue'
import BankEngineProposal from '@/app/features/bank/components/BankEngineProposal.vue'
import BankFactsCard from '@/app/features/bank/components/BankFactsCard.vue'
import BankSlaBadge from '@/app/features/bank/components/BankSlaBadge.vue'
import { useApplication } from '@/app/composables/useApplication'
import { useApplicationExplanation } from '@/app/composables/useApplicationExplanation'
import { useBankDecision } from '@/app/composables/useBankDecision'
import { useBankDossier } from '@/app/composables/useBankDossier'
import { useBankNextApplication } from '@/app/composables/useBankNextApplication'
import { useCompanyNames } from '@/app/composables/useCompanyNames'
import { useFormatters } from '@/app/composables/useFormatters'
import { useWorldClock } from '@/app/composables/useWorldClock'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'

const MANUAL_REASON_KIND = 'manual'

const props = defineProps<{
  inn: string
  applicationId: string
}>()

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()
const { formatCurrency, formatTerm } = useFormatters()
const { getCompanyName } = useCompanyNames()
// Срок рассмотрения — отсчётом по часам мира
const { now } = useWorldClock()
// После решения — сразу следующая заявка в очереди
const { nextItem, isShown: isNextShown, loadNext } = useBankNextApplication(() => props.applicationId)

const {
  application,
  events,
  isLoading,
  error,
  isNotFound,
  hasAction,
  loadApplication,
  refresh,
} = useApplication(() => props.applicationId)

// Досье и объяснение перечитываем, когда заявка изменилась: решение, подпись, статус
const version = computed(() => application.value?.updatedAt ?? null)
const explanationKey = computed(() => (application.value?.decision ? application.value.updatedAt : null))

const { dossier, isLoading: isDossierLoading, error: dossierError, loadDossier } = useBankDossier(
  () => props.applicationId,
  version,
)

const {
  explanation,
  isLoading: isExplanationLoading,
  error: explanationError,
  loadExplanation,
} = useApplicationExplanation(() => props.applicationId, explanationKey)

const { pendingCommand, decide, confirm } = useBankDecision(() => props.applicationId, refresh)

// Короткое название («ООО «Ромашка»») понятнее полного юридического из реестра, поэтому оно в приоритете
const companyTitle = computed(() =>
  getCompanyName.value(application.value?.companyInn ?? '') || dossier.value?.facts.name || props.inn,
)

// Что сейчас может сделать этот сотрудник — решает бэкенд
const canConfirm = computed(() => hasAction(ApplicationActionEnum.Confirm) && Boolean(application.value?.pendingDecision))
const canDecide = computed(() => hasAction(ApplicationActionEnum.Decide))
const isWaitingSecondKey = computed(() => !canConfirm.value && Boolean(application.value?.pendingDecision))
const isUnderReview = computed(() => application.value?.status === ApplicationDetailStatusEnum.UnderReview)

const requestRows = computed(() => {
  const request = application.value?.request

  if (!request) return []

  return [
    { key: 'product', label: t('bank.dossier.product'), value: t(`application.product.${request.product}`) },
    { key: 'amount', label: t('bank.dossier.amount'), value: formatCurrency(request.amount, 'RUB') },
    { key: 'term', label: t('bank.dossier.term'), value: request.termMonths ? formatTerm(request.termMonths) : '—' },
    { key: 'goal', label: t('bank.dossier.goal'), value: request.goal ? t(`application.goal.${request.goal}`) : '—' },
    { key: 'consent', label: t('bank.dossier.consent'), value: application.value?.consentBki ? t('bank.dossier.yes') : t('bank.dossier.no') },
  ]
})

// Причины, из-за которых нужен человек, — первыми и с акцентом; без повторяющейся метки над каждой
const reasons = computed(() =>
  (application.value?.decision?.reasons ?? [])
    .map((reason) => ({ code: reason.code, text: reason.text, isManual: reason.kind === MANUAL_REASON_KIND }))
    .sort((a, b) => Number(b.isManual) - Number(a.isManual)),
)

const nextRoute = computed(() =>
  nextItem.value ? { name: 'bank-dossier', params: { inn: props.inn, applicationId: nextItem.value.id } } : null,
)
const nextTitle = computed(() => {
  const item = nextItem.value

  if (!item) return ''

  return t('bank.next.item', {
    name: getCompanyName.value(item.inn) || t('bank.queue.companyInn', { inn: item.inn }),
    product: t(`application.product.${item.request.product}`),
    amount: formatCurrency(item.request.amount, 'RUB'),
  })
})
const queueRoute = computed(() => ({ name: 'bank-queue', params: { inn: props.inn } }))

const notes = computed(() => [application.value?.pendingDecision, application.value?.bankDecision].flatMap((note) => (note ? [note] : [])))

async function handleDecide(form: Parameters<typeof decide>[0]) {
  if (await decide(form)) loadNext()
}

async function handleConfirm(form: Parameters<typeof confirm>[0]) {
  if (await confirm(form)) loadNext()
}
const isFromApplications = computed(() => route.query.from === 'applications')

const backRoute = computed(() => ({
  name: isFromApplications.value ? 'bank-applications' : 'bank-queue',
  params: { inn: props.inn },
}))

const backLabel = computed(() => (isFromApplications.value ? t('bank.dossier.backToApplications') : t('bank.dossier.back')))
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <ApplicationPageSkeleton v-if="isLoading && !application" />

    <div
      v-else-if="isNotFound"
      class="flex flex-col items-center rounded-3xl border-dashed bg-fino-surface px-6 py-12 text-center border-2
             border-fino-line/40"
    >
      <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary border-2 border-fino-line">
        <i
          class="pi pi-search text-2xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 text-base font-semibold text-fino-text">
        {{ t('application.notFound') }}
      </p>

      <RouterLink
        :to="backRoute"
        class="mt-3 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        {{ backLabel }}
      </RouterLink>
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('application.detailLoadError')"
      @retry="loadApplication"
    />

    <template v-else-if="application">
      <!-- Заголовок -->
      <div>
        <RouterLink
          :to="backRoute"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ backLabel }}
        </RouterLink>

        <div class="mt-3 flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <h1 class="break-words text-3xl font-black text-fino-text sm:text-5xl">
              {{ companyTitle }}
            </h1>

            <p class="mt-1 text-sm text-fino-text-muted">
              {{ t('bank.queue.companyInn', { inn: application.companyInn }) }}
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <BankSlaBadge
              :sla-until="isUnderReview ? application.slaUntil : null"
              :flags="application.flags"
              :now="now"
            />

            <ApplicationStatusBadge :status="application.status" />
          </div>
        </div>

        <ApplicationFlags
          class="mt-3"
          :flags="application.flags"
        />
      </div>

      <!-- Решение принято — сразу следующая заявка, без возврата в очередь -->
      <section
        v-if="isNextShown"
        class="flex animate-fade-up flex-col gap-3 rounded-3xl bg-fino-lime-soft p-4 motion-reduce:animate-none sm:flex-row
               sm:items-center sm:justify-between sm:p-5 border-2 border-fino-line"
        role="status"
      >
        <div class="min-w-0">
          <p class="text-sm font-semibold text-fino-text">
            {{ t('bank.next.done') }}
          </p>
          <p class="mt-0.5 break-words text-sm text-fino-text-muted">
            {{ nextItem ? nextTitle : t('bank.next.empty') }}
          </p>
        </div>

        <RouterLink
          :to="nextRoute ?? queueRoute"
          class="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
                 font-semibold text-primary-contrast focus-visible:outline-2 focus-visible:outline-offset-2
                 focus-visible:outline-primary btn-key"
        >
          {{ nextItem ? t('bank.next.open') : t('bank.next.toQueue') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </RouterLink>
      </section>

      <div class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div class="flex min-w-0 flex-col gap-6">
          <!-- 1. Почему нужен человек и что просил клиент -->
          <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <article class="flex min-w-0 flex-col gap-4 card-key p-5">
              <h2 class="text-sm font-semibold text-fino-text">
                {{ t('bank.dossier.reasons') }}
              </h2>

              <p
                v-if="!reasons.length"
                class="text-sm text-fino-text-muted"
              >
                {{ t('bank.dossier.noReasons') }}
              </p>

              <ul
                v-else
                class="flex flex-col gap-2"
              >
                <li
                  v-for="reason in reasons"
                  :key="reason.code"
                  class="flex items-start gap-2 rounded-xl px-3 py-2 text-sm text-fino-text"
                  :class="reason.isManual ? 'bg-fino-accent' : 'bg-fino-surface-secondary'"
                >
                  <i
                    :class="reason.isManual ? 'pi pi-user text-primary' : 'pi pi-info-circle text-fino-text-muted'"
                    class="mt-0.5 text-xs"
                    aria-hidden="true"
                  />
                  <span class="min-w-0 break-words">{{ reason.text }}</span>
                </li>
              </ul>
            </article>

            <article class="flex min-w-0 flex-col gap-4 card-key p-5">
              <h2 class="text-sm font-semibold text-fino-text">
                {{ t('bank.dossier.request') }}
              </h2>

              <dl class="flex flex-col gap-1.5 text-sm">
                <div
                  v-for="row in requestRows"
                  :key="row.key"
                  class="flex justify-between gap-3"
                >
                  <dt class="shrink-0 text-fino-text-muted">
                    {{ row.label }}
                  </dt>
                  <dd class="min-w-0 break-words text-right font-semibold text-fino-text">
                    {{ row.value }}
                  </dd>
                </div>
              </dl>
            </article>
          </div>

          <!-- 2. Факты с источниками и свежестью — до решения -->
          <BankFactsCard
            :dossier="dossier"
            :is-loading="isDossierLoading"
            :has-error="dossierError"
            @retry="loadDossier"
          />

          <!-- 3. Подсказка движка — свёрнута и после фактов: сначала своё суждение -->
          <BankEngineProposal
            v-if="canDecide"
            :proposal="application.offer"
          />

          <!-- 4. Решение: набор элементов зависит от того, что бэкенд разрешил сотруднику -->
          <section
            class="flex min-w-0 flex-col gap-5 card-key p-5 sm:p-6"
            :aria-label="t('bank.decision.title')"
          >
            <BankConfirmPanel
              v-if="canConfirm && application.pendingDecision"
              :pending="application.pendingDecision"
              :pending-command="pendingCommand"
              @confirm="handleConfirm"
            />

            <BankDecisionPanel
              v-else-if="canDecide"
              :key="application.id"
              :request="application.request"
              :pending-command="pendingCommand"
              @decide="handleDecide"
            />

            <div
              v-else
              class="flex items-start gap-4"
            >
              <span
                class="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-fino-surface-secondary text-fino-text-muted"
                aria-hidden="true"
              >
                <i
                  :class="isWaitingSecondKey ? 'pi pi-key' : 'pi pi-info-circle'"
                  class="text-xl"
                />
              </span>

              <div class="min-w-0">
                <h2 class="text-lg font-bold tracking-tight text-fino-text">
                  {{ isWaitingSecondKey ? t('bank.decision.waitingTitle') : t('bank.decision.closedTitle') }}
                </h2>

                <p class="mt-1 text-sm leading-relaxed text-fino-text-muted">
                  {{ isWaitingSecondKey
                    ? t('bank.decision.waitingText')
                    : isUnderReview
                      ? t('bank.decision.notYoursText')
                      : t('bank.decision.closedText') }}
                </p>
              </div>
            </div>

            <div
              v-if="notes.length"
              class="flex flex-col gap-3"
            >
              <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
                {{ t('bank.decision.history') }}
              </p>

              <BankDecisionNote
                v-for="note in notes"
                :key="note.at + note.action"
                :note="note"
              />
            </div>
          </section>
        </div>

        <aside class="flex min-w-0 flex-col gap-6">
          <ApplicationExplanationCard
            v-if="application.decision"
            :explanation="explanation"
            is-path-hidden
            is-score-breakdown-visible
            :is-loading="isExplanationLoading"
            :has-error="explanationError"
            @retry="loadExplanation"
          />

          <div class="card-key p-5">
            <ApplicationTimeline
              :events="events"
              :is-limit="application?.loan?.isLimit ?? false"
            />
          </div>
        </aside>
      </div>
    </template>
  </div>
</template>
