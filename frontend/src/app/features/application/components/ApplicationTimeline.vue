<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApplicationWorldChange } from '@/app/composables/useApplicationWorldChange'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationAskEnum } from '@/app/types/application/application-ask-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'
import type { Nullable } from '@/app/types/nullable'

interface TimelineItemInterface {
  id: string
  icon: string
  title: string
  detail: string
  author: string
  at: string
}

type ItemDraft = Omit<TimelineItemInterface, 'id' | 'at' | 'author' | 'detail'> & { author?: string; detail?: string }

const STATUS_CHANGED = 'application.status_changed'
const STEP_CHANGED = 'step.changed'
const SECOND_IN_MS = 1000

// Шаги конвейера: их сворачиваем в одну строку «Банк проверил данные»
const PIPELINE_ACTOR = 'worker'
// Смену статуса после решения движка уже описывает само решение
const ENGINE_ACTOR = 'engine'
// Итог голосования участников бэкенд пишет причиной перехода
const APPROVAL_AGREED_REASON = 'участники согласовали'
const APPROVAL_REJECTED_REASON = 'участники не согласовали'

const props = defineProps<{
  events: ApplicationEventInterface[]
  // Овердрафт: выдача — это подключённый лимит, а не деньги на счёте
  isLimit: boolean
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime, formatDuration } = useFormatters()
const { isWorldChange, describeChange } = useApplicationWorldChange(() => props.events)

function getAuthor(event: ApplicationEventInterface): string {
  return event.author ? [event.author.name, event.author.caption].filter(Boolean).join(' · ') : ''
}

function isPipelineStep(event: ApplicationEventInterface): boolean {
  if (event.type === STEP_CHANGED) return true

  return event.type === STATUS_CHANGED
    && event.actor === PIPELINE_ACTOR
    && event.payload.to === ApplicationDetailStatusEnum.Checking
}

function describeDecision(event: ApplicationEventInterface): ItemDraft {
  const outcome = String(event.payload.outcome)
  const reasons = Array.isArray(event.payload.reasons) ? (event.payload.reasons as { code: string }[]) : []
  const isCorporateApproval = reasons.some((reason) => reason.code === ApplicationAskEnum.CorpApproval)

  return {
    icon: 'pi pi-verified',
    title: isCorporateApproval ? t('application.timeline.decision.CORP_APPROVAL') : t(`application.timeline.decision.${outcome}`),
  }
}

// Смена статуса человеком, банком или таймером; null — шаг, который уже описан другим событием
function describeStatusChange(event: ApplicationEventInterface): Nullable<ItemDraft> {
  const { to, from, reason } = event.payload
  const reasonText = String(reason ?? '')

  if (isWorldChange(event)) {
    return { icon: 'pi pi-sync', title: t('application.timeline.worldChanged'), detail: describeChange(event) }
  }

  if (event.actor === ENGINE_ACTOR) return null

  switch (to) {
    case ApplicationDetailStatusEnum.Draft:
      return { icon: 'pi pi-file-edit', title: t('application.timeline.created') }
    case ApplicationDetailStatusEnum.Submitted:
      return { icon: 'pi pi-send', title: t('application.timeline.submitted') }
    case ApplicationDetailStatusEnum.Checking:
    case ApplicationDetailStatusEnum.UnderReview:
      if (from === ApplicationDetailStatusEnum.InfoRequested) {
        // Голосование участников закрылось «за» — или клиент ответил на дозапрос
        return reasonText.startsWith(APPROVAL_AGREED_REASON)
          ? { icon: 'pi pi-users', title: t('application.timeline.approvalAgreed'), author: '' }
          : { icon: 'pi pi-reply', title: t('application.timeline.answered') }
      }

      return event.actor === PIPELINE_ACTOR
        ? { icon: 'pi pi-exclamation-circle', title: t('application.timeline.disburseDelayed') }
        : null
    case ApplicationDetailStatusEnum.InfoRequested:
      return { icon: 'pi pi-comment', title: t('application.timeline.bankAsked') }
    case ApplicationDetailStatusEnum.Offered:
      return { icon: 'pi pi-verified', title: t('application.timeline.bankApproved') }
    case ApplicationDetailStatusEnum.Signing:
      return { icon: 'pi pi-check', title: t('application.timeline.accepted') }
    case ApplicationDetailStatusEnum.Signed:
      return { icon: 'pi pi-pen-to-square', title: t('application.timeline.signed') }
    case ApplicationDetailStatusEnum.Disbursing:
      return null
    case ApplicationDetailStatusEnum.Issued:
      return {
        icon: 'pi pi-check-circle',
        title: props.isLimit ? t('application.timeline.issuedLimit') : t('application.timeline.issuedLoan'),
        author: t('application.timeline.bank'),
      }
    case ApplicationDetailStatusEnum.Rejected:
      return event.actor === PIPELINE_ACTOR
        ? { icon: 'pi pi-times-circle', title: t('application.timeline.finalCheckRejected'), author: t('application.timeline.bank') }
        : { icon: 'pi pi-times-circle', title: t('application.timeline.bankRejected') }
    case ApplicationDetailStatusEnum.Declined:
      return { icon: 'pi pi-ban', title: t('application.timeline.declined') }
    case ApplicationDetailStatusEnum.Withdrawn:
      return reasonText.startsWith(APPROVAL_REJECTED_REASON)
        ? { icon: 'pi pi-users', title: t('application.timeline.approvalRejected'), author: '' }
        : { icon: 'pi pi-undo', title: t('application.timeline.withdrawn') }
    case ApplicationDetailStatusEnum.Expired:
      return { icon: 'pi pi-clock', title: t('application.timeline.expired'), author: t('application.timeline.bank') }
    default:
      return null
  }
}

function describeEvent(event: ApplicationEventInterface): Nullable<ItemDraft> {
  switch (event.type) {
    case STATUS_CHANGED:
      return describeStatusChange(event)
    case 'decision.made':
      return describeDecision(event)
    case 'decision.awaiting_second_key':
      return { icon: 'pi pi-key', title: t('application.timeline.awaitingSecondKey') }
    case 'decision.second_key_returned':
      return { icon: 'pi pi-replay', title: t('application.timeline.secondKeyReturned') }
    case 'signature.added':
      return { icon: 'pi pi-pen-to-square', title: t('application.timeline.signatureAdded') }
    case 'approval.voted':
      return {
        icon: 'pi pi-users',
        title: event.payload.vote === 'against' ? t('application.timeline.vote.against') : t('application.timeline.vote.for'),
      }
    case 'application.flagged':
      return event.payload.flag === ApplicationFlagEnum.SlaBreach
        ? { icon: 'pi pi-hourglass', title: t('application.timeline.slaBreach'), author: t('application.timeline.bank') }
        : null
    case 'provisional.confirmed':
      return { icon: 'pi pi-check', title: t('application.timeline.provisionalConfirmed'), author: t('application.timeline.bank') }
    default:
      return { icon: 'pi pi-circle', title: t('application.timeline.other') }
  }
}

// «Банк проверил данные за 2 сек.»: от старта конвейера до следующего события; без него — ещё проверяет
function describePipeline(startedAt: string, finishedAt: Nullable<string>): string {
  if (!finishedAt) return t('application.timeline.checking')

  const seconds = (new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / SECOND_IN_MS

  return seconds < 1
    ? t('application.timeline.checkedInstantly')
    : t('application.timeline.checked', { duration: formatDuration(Math.round(seconds)) })
}

// В истории — только события людей и итоги; технические шаги конвейера — одной строкой
const items = computed<TimelineItemInterface[]>(() => {
  const result: TimelineItemInterface[] = []
  const events = props.events
  const isSubmitted = events.some((event) => event.payload.to === ApplicationDetailStatusEnum.Submitted)

  for (let index = 0; index < events.length; index++) {
    const event = events[index]

    if (isPipelineStep(event)) {
      let last = index

      while (last + 1 < events.length && isPipelineStep(events[last + 1])) last++

      result.push({
        id: `pipeline-${event.id}`,
        icon: 'pi pi-database',
        title: describePipeline(event.at, events[last + 1]?.at ?? null),
        detail: '',
        author: t('application.timeline.bank'),
        at: event.at,
      })

      index = last
      continue
    }

    // Черновик, который подали, отдельной строкой не показываем
    if (event.type === STATUS_CHANGED && event.payload.to === ApplicationDetailStatusEnum.Draft && isSubmitted) continue

    const item = describeEvent(event)

    if (!item) continue

    result.push({
      id: String(event.id),
      icon: item.icon,
      title: item.title,
      detail: item.detail ?? '',
      author: item.author ?? getAuthor(event),
      at: event.at,
    })
  }

  // Новые события сверху
  return result.reverse()
})

function formatTime(at: string): string {
  return formatDateTime(at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <section :aria-label="t('application.timeline.title')">
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('application.timeline.title') }}
    </h2>

    <TransitionGroup
      tag="ol"
      class="mt-4 flex flex-col"
      enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
      enter-from-class="-translate-y-2 opacity-0"
    >
      <li
        v-for="item in items"
        :key="item.id"
        class="relative flex gap-3 pb-4 last:pb-0"
      >
        <span
          class="absolute top-7 bottom-0 left-3.5 w-px bg-fino-border last:hidden"
          aria-hidden="true"
        />

        <span
          class="relative flex size-7 shrink-0 items-center justify-center rounded-full
                 bg-fino-surface-secondary text-fino-text-muted"
          aria-hidden="true"
        >
          <i
            :class="item.icon"
            class="text-xs"
          />
        </span>

        <div class="min-w-0 pt-0.5">
          <p class="break-words text-sm text-fino-text">
            {{ item.title }}
          </p>

          <p
            v-if="item.detail"
            class="mt-0.5 break-words text-xs text-fino-text-muted"
          >
            {{ item.detail }}
          </p>

          <p class="mt-0.5 text-xs text-fino-text-muted">
            <span
              v-if="item.author"
              class="font-medium text-fino-text"
            >{{ item.author }}</span>
            <span v-if="item.author"> · </span>{{ formatTime(item.at) }}
          </p>
        </div>
      </li>
    </TransitionGroup>
  </section>
</template>
