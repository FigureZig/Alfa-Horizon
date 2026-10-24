import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { readLastPersonaId, useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { CompanyAccessInterface } from '@/app/types/company/company-access-interface'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxEventCreateDto } from '@/app/types/sandbox/sandbox-world-dto'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type {
  SandboxScenarioInterface,
  SandboxScenarioStepInterface,
} from '@/app/types/sandbox/sandbox-scenario-interface'

// Действие в кабинете → действие шага сценария (как его называет бэкенд в /sandbox/scenarios)
const ACTION_TO_STEP: Record<string, string> = {
  create: 'create',
  submit: 'submit',
  accept_offer: 'accept',
  sign: 'sign',
  vote: 'vote',
  answer_info: 'answer',
  approve: 'bank',
  reject: 'bank',
  request_info: 'bank',
  confirm: 'confirm',
  return: 'confirm',
}

// Шаги, которые закрываются сами: банк работает, клиент ждёт смену статуса
const SYSTEM_ACTION = 'run'
const EVENT_ACTION = 'event'
// «Попробуйте — банк не даст»: результат виден только глазами, шаг закрывают кнопкой
const FORBIDDEN_ACTION = 'forbidden'

const STORAGE_KEY = 'fino-scenario-run'
// По этим статусам видно, что заявка ушла вперёд. «Подана», «Проверяем», «Дозапрос», «У специалиста» повторяются
// в одном сценарии (до и после голосования), по ним догонять нельзя
const PROGRESS_STATUSES: ApplicationDetailStatusEnum[] = [
  ApplicationDetailStatusEnum.Offered,
  ApplicationDetailStatusEnum.Signing,
  ApplicationDetailStatusEnum.Signed,
  ApplicationDetailStatusEnum.Disbursing,
  ApplicationDetailStatusEnum.Issued,
  ApplicationDetailStatusEnum.Rejected,
  ApplicationDetailStatusEnum.Declined,
  ApplicationDetailStatusEnum.Withdrawn,
  ApplicationDetailStatusEnum.Expired,
]

interface StoredRunInterface {
  scenario: SandboxScenarioInterface
  doneSteps: number[]
  applicationId: Nullable<string>
}

function readStored(): Nullable<StoredRunInterface> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    const value = raw ? (JSON.parse(raw) as StoredRunInterface) : null

    return Array.isArray(value?.doneSteps) ? value : null
  } catch {
    return null
  }
}

// Прохождение одно на вкладку и переживает перезагрузку страницы
const stored = readStored()
const scenario = ref<Nullable<SandboxScenarioInterface>>(stored?.scenario ?? null)
// Выполненные шаги: люди могут сделать их не по порядку (Елена проголосовала раньше Алексея)
const doneSteps = ref<number[]>(stored?.doneSteps ?? [])
// Заявка сценария: появляется на шаге «создаёт заявку»
const applicationId = ref<Nullable<string>>(stored?.applicationId ?? null)
const status = ref<Nullable<ApplicationDetailStatusEnum>>(null)
// Статус заявки в момент, когда текущий шаг стал текущим: если он сменился — заявка ушла вперёд
const statusAtStep = ref<Nullable<ApplicationDetailStatusEnum>>(null)
const isBusy = ref(false)

watch([scenario, doneSteps, applicationId], () => {
  try {
    if (!scenario.value) {
      sessionStorage.removeItem(STORAGE_KEY)

      return
    }

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
      scenario: scenario.value,
      doneSteps: doneSteps.value,
      applicationId: applicationId.value,
    }))
  } catch {
    // Хранилище недоступно: прохождение живёт до перезагрузки
  }
}, { deep: true })

const steps = computed(() => scenario.value?.steps ?? [])
// Текущий шаг — первый невыполненный
const currentStep = computed(() => steps.value.find((step) => !doneSteps.value.includes(step.number)) ?? null)
const stepNumber = computed(() => currentStep.value?.number ?? Number.POSITIVE_INFINITY)
const isFinished = computed(() => Boolean(scenario.value) && !currentStep.value)
const doneCount = computed(() => steps.value.filter((step) => doneSteps.value.includes(step.number)).length)

watch(stepNumber, () => {
  statusAtStep.value = status.value
})

function isStepDone(step: SandboxScenarioStepInterface): boolean {
  return doneSteps.value.includes(step.number)
}

function isStepCurrent(step: SandboxScenarioStepInterface): boolean {
  return step.number === currentStep.value?.number
}

function markDone(numbers: number[]) {
  doneSteps.value = [...new Set([...doneSteps.value, ...numbers])].sort((first, second) => first - second)
}

/**
 * Догнать сценарий по статусу заявки.
 * Системный шаг закрывается, когда статус стал ожидаемым. А если статус сменился с момента, когда текущий шаг
 * стал текущим, и совпал с ожидаемым у одного из следующих шагов, — заявка ушла вперёд: всё до этого шага сделано
 * (например, кредит уже выдан, а голос одного из участников мы не увидели).
 */
function advanceByStatus() {
  for (;;) {
    const current = currentStep.value

    if (!current || !status.value) return

    if (current.action === SYSTEM_ACTION && current.expectedStatus === status.value) {
      markDone([current.number])
      continue
    }

    if (status.value === statusAtStep.value || !PROGRESS_STATUSES.includes(status.value)) return

    const reached = steps.value.find((step) => step.number >= current.number && step.expectedStatus === status.value)

    if (!reached) return

    markDone(steps.value.filter((step) => step.number <= reached.number).map((step) => step.number))
  }
}

export function useScenarioRun() {
  const $fetch = useApiFetch()
  const router = useRouter()
  const { t } = useI18n({ useScope: 'global' })
  const { loginAsPersona } = useSession()

  function start(value: SandboxScenarioInterface, fromStep = 1) {
    const isSameRun = scenario.value?.id === value.id

    scenario.value = value
    // Начали с шага N — всё до него считаем сделанным, а то, что после, — нет
    doneSteps.value = value.steps.filter((step) => step.number < fromStep).map((step) => step.number)

    // Сценарий с начала — заявку создадут заново
    if (!isSameRun || fromStep <= 1) {
      applicationId.value = null
      status.value = null
    }

    statusAtStep.value = status.value
  }

  function stop() {
    scenario.value = null
    doneSteps.value = []
    applicationId.value = null
    status.value = null
    statusAtStep.value = null
  }

  /**
   * Сообщение из кабинета: человек сделал действие с заявкой. Засчитываем ближайший невыполненный шаг
   * с этим действием и этим человеком — голос Елены не закроет шаг Алексея.
   */
  function reportAction(action: string, id: Nullable<string>, newStatus: Nullable<ApplicationDetailStatusEnum> = null) {
    if (!scenario.value || !currentStep.value) return

    if (id && (action === 'create' || !applicationId.value)) applicationId.value = id

    const personaId = readLastPersonaId()
    const step = steps.value.find((item) =>
      !isStepDone(item)
      && item.number >= (currentStep.value?.number ?? 0)
      && ACTION_TO_STEP[action] === item.action
      && (!item.user || item.user.id === personaId),
    )

    if (step) markDone([step.number])

    if (newStatus) {
      // Статус после своего же действия — не «заявка ушла вперёд»: догоняем только системные шаги
      statusAtStep.value = newStatus
      status.value = newStatus
    }

    advanceByStatus()
  }

  function reportStatus(id: string, newStatus: ApplicationDetailStatusEnum) {
    if (!scenario.value || id !== applicationId.value) return

    status.value = newStatus
    advanceByStatus()
  }

  // Куда вести человека шага: создать — в форму заявки с подставленными условиями, банк — в досье, участника — в голосование
  function getStepRoute(step: SandboxScenarioStepInterface, persona: SandboxPersonaInterface,
    companies: CompanyAccessInterface[]): RouteLocationRaw {
    const inn = scenario.value?.company.inn ?? persona.inn
    const id = applicationId.value

    if (persona.kind === SandboxPersonaKindEnum.Bank) {
      return id
        ? { name: 'bank-dossier', params: { inn: persona.inn, applicationId: id } }
        : { name: 'bank-queue', params: { inn: persona.inn } }
    }

    if (step.action === 'create') {
      const body = step.request.body ?? {}

      return {
        name: 'application-new',
        params: { inn },
        query: {
          product: String(body.product ?? ''),
          amount: String(body.amount ?? ''),
          term: String(body.term_months ?? ''),
          goal: String(body.goal ?? ''),
        },
      }
    }

    const access = companies.find((company) => company.inn === inn)

    if (access && !access.canView && access.canApprove) {
      return id ? { name: 'vote', params: { inn, applicationId: id } } : { name: 'votes', params: { inn } }
    }

    return id ? { name: 'application', params: { inn, applicationId: id } } : { name: 'applications', params: { inn } }
  }

  // Войти человеком шага и открыть нужную страницу
  async function goToStep(step: SandboxScenarioStepInterface): Promise<boolean> {
    if (!step.user || isBusy.value) return false

    isBusy.value = true

    try {
      const { persona, companies } = await loginAsPersona(step.user.id)

      await router.push(getStepRoute(step, persona, companies))

      return true
    } finally {
      isBusy.value = false
    }
  }

  // Событие реестра делает сам сценарий: применили — шаг пройден
  async function applyEvent(step: SandboxScenarioStepInterface) {
    if (!step.request.body || isBusy.value) return

    isBusy.value = true

    try {
      await sandboxService.createEvent($fetch, step.request.body as unknown as SandboxEventCreateDto)

      markDone([step.number])
      advanceByStatus()
    } finally {
      isBusy.value = false
    }
  }

  // Шаги «пробует — банк не даёт» и любые, которые нельзя заметить автоматически
  function confirmCurrentStep() {
    if (currentStep.value) markDone([currentStep.value.number])
  }

  // Что сделать на текущем шаге — словами, с названием кнопки в кабинете
  const currentHint = computed(() => {
    const step = currentStep.value

    if (!step) return ''
    if (step.action === SYSTEM_ACTION) return t('reviewer.tracker.hint.run')
    if (step.action === EVENT_ACTION) return t('reviewer.tracker.hint.event')
    if (step.action === FORBIDDEN_ACTION) return t('reviewer.tracker.hint.forbidden')

    return t(`reviewer.tracker.hint.${step.action}`)
  })

  return {
    scenario,
    stepNumber,
    applicationId,
    status,
    isBusy,
    steps,
    currentStep,
    currentHint,
    isFinished,
    doneCount,
    isStepDone,
    isStepCurrent,
    start,
    stop,
    reportAction,
    reportStatus,
    goToStep,
    applyEvent,
    confirmCurrentStep,
  }
}

export { EVENT_ACTION, FORBIDDEN_ACTION, SYSTEM_ACTION }
