import { computed, onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import type { AxiosResponse } from 'axios'
import { getSessionToken, isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { createIdempotencyKey } from '@/app/composables/useApplicationCreate'
import { useApplicationError } from '@/app/composables/useApplicationError'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'
import { ApplicationEventMapper } from '@/app/mappers/application-event.mapper'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApiResponse } from '@/app/types/api-response'
import type { ApplicationDto } from '@/app/types/application/application-dto'
import type { ApplicationInfoAnswerInterface } from '@/app/types/application/application-form-interface'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { ApplicationVoteEnum } from '@/app/types/application/application-vote-enum'
import type { Nullable } from '@/app/types/nullable'

class StreamUnavailableError extends Error {}

const STREAM_RETRY_DELAY = 3000

// Типы событий потока заявки: на каждый перечитываем заявку и историю
const STREAM_EVENT_TYPES = [
  'application.status_changed',
  'step.changed',
  'decision.made',
  'decision.awaiting_second_key',
  'decision.second_key_returned',
  'signature.added',
  'approval.voted',
  'application.flagged',
  'provisional.confirmed',
]

const FINAL_STATUSES: ApplicationDetailStatusEnum[] = [
  ApplicationDetailStatusEnum.Issued,
  ApplicationDetailStatusEnum.Rejected,
  ApplicationDetailStatusEnum.Declined,
  ApplicationDetailStatusEnum.Withdrawn,
  ApplicationDetailStatusEnum.Expired,
]

// Если живой поток недоступен, обновляем заявку опросом
const POLL_INTERVAL = 4000

type ApplicationResponse = AxiosResponse<ApiResponse<ApplicationDto>>

/**
 * Заявка с историей и командами. Кнопки определяет `availableActions` с бэкенда — права и статус не повторяем.
 * Страница обновляется сама: по событиям потока SSE, а при его сбое — опросом, пока заявка не завершена.
 */
export function useApplication(applicationId: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t } = useI18n({ useScope: 'global' })
  const { getApplicationErrorMessage } = useApplicationError()

  const application = ref<Nullable<ApplicationInterface>>(null)
  const events = ref<ApplicationEventInterface[]>([])
  const isLoading = ref(false)
  const error = ref(false)
  const isNotFound = ref(false)
  const pendingAction = ref<Nullable<ApplicationActionEnum>>(null)

  const isFinished = computed(() => Boolean(application.value && FINAL_STATUSES.includes(application.value.status)))

  let streamAbort: Nullable<AbortController> = null
  let lastEventId: Nullable<string> = null
  let pollTimer: ReturnType<typeof setInterval> | undefined
  let isRefreshing = false
  let isRefreshQueued = false

  function hasAction(action: ApplicationActionEnum): boolean {
    return Boolean(application.value?.availableActions.includes(action))
  }

  async function fetchApplicationWithEvents() {
    const id = toValue(applicationId)

    const [applicationResponse, eventsResponse] = await Promise.all([
      applicationsService.fetchApplication($fetch, id),
      applicationsService.fetchEvents($fetch, id),
    ])

    // Пока ждали ответ, пользователь мог уйти на другую заявку
    if (id !== toValue(applicationId)) return

    application.value = ApplicationMapper.toEntity(applicationResponse.data.data)
    events.value = eventsResponse.data.data.map((event) => ApplicationEventMapper.toEntity(event))
  }

  async function loadApplication() {
    isLoading.value = true
    error.value = false
    isNotFound.value = false

    try {
      await fetchApplicationWithEvents()
    } catch (err: unknown) {
      console.error('Application loading failed:', err)
      application.value = null
      isNotFound.value = isNotFoundError(err)
      error.value = !isNotFound.value
    } finally {
      isLoading.value = false
    }
  }

  // Тихое обновление: без skeleton, события потока приходят пачкой — склеиваем в один повтор
  async function refreshSilently() {
    if (isRefreshing) {
      isRefreshQueued = true
      return
    }

    isRefreshing = true

    try {
      await fetchApplicationWithEvents()
    } catch (err: unknown) {
      console.error('Application refresh failed:', err)
    } finally {
      isRefreshing = false

      if (isRefreshQueued) {
        isRefreshQueued = false
        refreshSilently()
      }
    }
  }

  // ── Живые обновления ─────────────────────────────────────────────────────────

  function closeLiveUpdates() {
    streamAbort?.abort()
    streamAbort = null
    clearInterval(pollTimer)
    pollTimer = undefined
  }

  function startPolling() {
    if (pollTimer) return

    pollTimer = setInterval(refreshSilently, POLL_INTERVAL)
  }

  // Блок потока: строки `id:` и `event:`; `snapshot` и пинги не меняют заявку, остальные события — повод перечитать её
  function handleStreamBlock(block: string) {
    let type = ''

    for (const line of block.split('\n')) {
      if (line.startsWith('id:')) lastEventId = line.slice(3).trim()
      if (line.startsWith('event:')) type = line.slice(6).trim()
    }

    if (STREAM_EVENT_TYPES.includes(type)) refreshSilently()
  }

  // EventSource не умеет передавать заголовок Authorization, поэтому поток читаем через fetch — с токеном этой сессии
  async function readStream(signal: AbortSignal) {
    const token = getSessionToken()
    const headers: Record<string, string> = { Accept: 'text/event-stream' }

    if (token) headers.Authorization = `Bearer ${token}`
    if (lastEventId) headers['Last-Event-ID'] = lastEventId

    const baseUrl = import.meta.env.VITE_API_BASE_URL
    const response = await fetch(`${baseUrl}/v1/applications/${encodeURIComponent(toValue(applicationId))}/stream`, {
      headers,
      signal,
    })

    // Нет доступа или заявки — поток не поможет, дальше обновляемся опросом
    if (!response.ok || !response.body) throw new StreamUnavailableError()

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let buffer = ''

    for (;;) {
      const { done, value } = await reader.read()

      if (done) return

      buffer += value.replace(/\r\n/g, '\n')

      const blocks = buffer.split('\n\n')

      buffer = blocks.pop() ?? ''
      blocks.forEach(handleStreamBlock)
    }
  }

  // Сервер закрывает поток по таймауту и в конце заявки: в первом случае переподключаемся с последнего события
  async function followStream(signal: AbortSignal) {
    while (!signal.aborted) {
      try {
        await readStream(signal)
      } catch (err: unknown) {
        if (signal.aborted) return

        if (err instanceof StreamUnavailableError) {
          startPolling()
          return
        }
      }

      if (signal.aborted || isFinished.value) return

      await new Promise((resolve) => setTimeout(resolve, STREAM_RETRY_DELAY))
    }
  }

  function openLiveUpdates() {
    if (streamAbort || pollTimer) return

    streamAbort = new AbortController()
    followStream(streamAbort.signal)
  }

  // ── Команды ──────────────────────────────────────────────────────────────────

  async function runAction(action: ApplicationActionEnum, request: () => Promise<ApplicationResponse>): Promise<boolean> {
    if (pendingAction.value) return false

    pendingAction.value = action

    try {
      const { data } = await request()

      application.value = ApplicationMapper.toEntity(data.data)

      toast.add({
        severity: 'success',
        summary: t('toast.success'),
        detail: t(`toast.application.${action}`),
        life: 4000,
      })

      refreshSilently()

      return true
    } catch (err: unknown) {
      console.error(`Application action ${action} failed:`, err)

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: getApplicationErrorMessage(err),
        life: 6000,
      })

      // Статус мог измениться (таймер, воркер) — подтягиваем свежее состояние и кнопки
      refreshSilently()

      return false
    } finally {
      pendingAction.value = null
    }
  }

  function submit() {
    return runAction(ApplicationActionEnum.Submit, () =>
      applicationsService.submitApplication($fetch, toValue(applicationId), createIdempotencyKey()))
  }

  function withdraw() {
    return runAction(ApplicationActionEnum.Withdraw, () =>
      applicationsService.withdrawApplication($fetch, toValue(applicationId)))
  }

  function acceptOffer(variant: number) {
    return runAction(ApplicationActionEnum.AcceptOffer, () =>
      applicationsService.acceptOffer($fetch, toValue(applicationId), variant))
  }

  function declineOffer() {
    return runAction(ApplicationActionEnum.DeclineOffer, () =>
      applicationsService.declineOffer($fetch, toValue(applicationId)))
  }

  function sign() {
    return runAction(ApplicationActionEnum.Sign, () =>
      applicationsService.signApplication($fetch, toValue(applicationId)))
  }

  function answerInfo(answer: ApplicationInfoAnswerInterface) {
    return runAction(ApplicationActionEnum.AnswerInfo, () =>
      applicationsService.answerInfoRequest($fetch, toValue(applicationId), ApplicationMapper.toInfoAnswerPayload(answer)))
  }

  function vote(choice: ApplicationVoteEnum) {
    return runAction(ApplicationActionEnum.Vote, () =>
      applicationsService.voteForLargeDeal($fetch, toValue(applicationId), choice))
  }

  function onApplicationChange() {
    closeLiveUpdates()
    application.value = null
    events.value = []
    loadApplication()
  }

  // Поток нужен, пока заявка не завершена: у конечных статусов бэкенд сам закрывает поток
  function onStatusChange() {
    if (!application.value) return

    if (isFinished.value) {
      closeLiveUpdates()
    } else {
      openLiveUpdates()
    }
  }

  watch(() => toValue(applicationId), onApplicationChange, { immediate: true })
  watch(() => application.value?.status, onStatusChange)
  onBeforeUnmount(closeLiveUpdates)

  return {
    application,
    events,
    isLoading,
    error,
    isNotFound,
    isFinished,
    pendingAction,
    hasAction,
    loadApplication,
    refresh: refreshSilently,
    submit,
    withdraw,
    acceptOffer,
    declineOffer,
    sign,
    answerInfo,
    vote,
  }
}
