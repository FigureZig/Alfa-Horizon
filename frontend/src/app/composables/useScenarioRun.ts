import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
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
const FINISHED = Number.POSITIVE_INFINITY

interface StoredRunInterface {
  scenario: SandboxScenarioInterface
  stepNumber: number
  applicationId: Nullable<string>
}

function readStored(): Nullable<StoredRunInterface> {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)

    return raw ? (JSON.parse(raw) as StoredRunInterface) : null
  } catch {
    return null
  }
}

// Прохождение одно на вкладку и переживает перезагрузку страницы
const stored = readStored()
const scenario = ref<Nullable<SandboxScenarioInterface>>(stored?.scenario ?? null)
// Шаг, который нужно сделать сейчас; FINISHED — сценарий пройден
const stepNumber = ref(stored?.stepNumber === null ? FINISHED : stored?.stepNumber ?? 0)
// Заявка сценария: появляется на шаге «создаёт заявку»
const applicationId = ref<Nullable<string>>(stored?.applicationId ?? null)
const status = ref<Nullable<ApplicationDetailStatusEnum>>(null)
const isBusy = ref(false)

watch([scenario, stepNumber, applicationId], () => {
  try {
    if (!scenario.value) {
      sessionStorage.removeItem(STORAGE_KEY)

      return
    }

    // JSON не хранит Infinity: пройденный сценарий сохраняем как null
    const value = { scenario: scenario.value, stepNumber: Number.isFinite(stepNumber.value) ? stepNumber.value : null,
      applicationId: applicationId.value }

    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value))
  } catch {
    // Хранилище недоступно: прохождение живёт до перезагрузки
  }
})

const steps = computed(() => scenario.value?.steps ?? [])
const currentStep = computed(() => steps.value.find((step) => step.number === stepNumber.value) ?? null)
const isFinished = computed(() => Boolean(scenario.value) && !currentStep.value)
const doneCount = computed(() => steps.value.filter((step) => step.number < stepNumber.value).length)

function isStepDone(step: SandboxScenarioStepInterface): boolean {
  return step.number < stepNumber.value
}

function isStepCurrent(step: SandboxScenarioStepInterface): boolean {
  return step.number === stepNumber.value
}

function advance() {
  const next = steps.value.find((step) => step.number > stepNumber.value)

  stepNumber.value = next ? next.number : FINISHED
  advanceByStatus()
}

// Системный шаг закрывается, когда заявка пришла в ожидаемый статус
function advanceByStatus() {
  while (
    currentStep.value?.action === SYSTEM_ACTION
    && status.value
    && currentStep.value.expectedStatus === status.value
  ) {
    const next = steps.value.find((step) => step.number > stepNumber.value)

    stepNumber.value = next ? next.number : FINISHED
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
    stepNumber.value = value.steps.find((step) => step.number >= fromStep)?.number ?? FINISHED

    // Сценарий с начала — заявку создадут заново
    if (!isSameRun || fromStep <= 1) {
      applicationId.value = null
      status.value = null
    }
  }

  function stop() {
    scenario.value = null
    stepNumber.value = 0
    applicationId.value = null
    status.value = null
  }

  // Сообщение из кабинета: пользователь сделал действие с заявкой
  function reportAction(action: string, id: Nullable<string>, newStatus: Nullable<ApplicationDetailStatusEnum> = null) {
    if (!scenario.value || !currentStep.value) return

    if (id && (action === 'create' || !applicationId.value)) applicationId.value = id
    if (newStatus) status.value = newStatus

    if (ACTION_TO_STEP[action] === currentStep.value.action) {
      advance()
    } else {
      advanceByStatus()
    }
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

      if (isStepCurrent(step)) advance()
    } finally {
      isBusy.value = false
    }
  }

  // Шаги «пробует — банк не даёт» и любые, которые нельзя заметить автоматически
  function confirmCurrentStep() {
    if (currentStep.value) advance()
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
