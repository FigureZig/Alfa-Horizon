<script setup lang="ts">
import { computed, onMounted, reactive, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Checkbox from 'primevue/checkbox'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import RadioButton from 'primevue/radiobutton'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import SandboxPersonaBuilderSkeleton from '@/app/features/sandbox/components/SandboxPersonaBuilderSkeleton.vue'
import SandboxPersonaChoice from '@/app/features/sandbox/components/SandboxPersonaChoice.vue'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import SandboxPersonaFlagsPicker from '@/app/features/sandbox/components/SandboxPersonaFlagsPicker.vue'
import SandboxPersonaGroup from '@/app/features/sandbox/components/SandboxPersonaGroup.vue'
import SandboxPersonaPreview from '@/app/features/sandbox/components/SandboxPersonaPreview.vue'
import SandboxPersonaPreviewBar from '@/app/features/sandbox/components/SandboxPersonaPreviewBar.vue'
import { getApiProblem, useApiFetch } from '@/app/composables/useApiFetch'
import { useSandboxPersonaPreview } from '@/app/composables/useSandboxPersonaPreview'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaOptionsMapper } from '@/app/mappers/sandbox-persona-options.mapper'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'
import { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaGroupInterface } from '@/app/types/sandbox/sandbox-persona-group-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type { SandboxPersonaOptionsInterface } from '@/app/types/sandbox/sandbox-persona-options-interface'

const ANSWERS_STORAGE_KEY = 'fino-company-answers'
const FULL_NAME_MAX_LENGTH = 80
const INN_PATTERN = /^(\d{10}|\d{12})$/

const CHOICE_FIELDS = ['seasonality', 'stability', 'trend', 'channel', 'loans', 'delays'] as const

type BuilderStage = 'interview' | 'result'

// Интервью вместо бланка: три вопроса до первого результата, остальное — в «Уточнить»
const INTERVIEW_QUESTIONS = 3

// Сколько приходит на счёт — диапазонами; в расчёт идёт середина диапазона
const REVENUE_RANGES = [
  { id: 'upTo500k', value: 300_000 },
  { id: 'upTo3m', value: 1_500_000 },
  { id: 'upTo10m', value: 5_000_000 },
  { id: 'over10m', value: 15_000_000 },
] as const

// Кто в компании — словами человека; форма и устройство компании выводятся из ответа
const TEAM_OPTIONS = [
  { id: 'solo', form: LegalFormEnum.SoleProprietor, structure: null },
  { id: 'partners', form: LegalFormEnum.Llc, structure: 'partners' },
  { id: 'hiredDirector', form: LegalFormEnum.Llc, structure: 'hired_director' },
  { id: 'jointDirectors', form: LegalFormEnum.Llc, structure: 'two_directors_joint' },
  { id: 'independentDirectors', form: LegalFormEnum.Llc, structure: 'two_directors_independent' },
] as const

type RevenueRange = (typeof REVENUE_RANGES)[number]
type TeamOption = (typeof TEAM_OPTIONS)[number]

// Точные цифры: пустые бэкенд выводит из простых ответов; ключ ответа — для подсветки и подписи
const EXACT_FIELDS = [
  { key: 'inflowCv', field: 'inflow_cv', max: 2, fractionDigits: 2 },
  { key: 'inflowTrend', field: 'inflow_trend', max: 1, fractionDigits: 2 },
  { key: 'debtLoad', field: 'debt_load', max: 2, fractionDigits: 2 },
  { key: 'profitMargin', field: 'profit_margin', max: 1, fractionDigits: 2 },
  { key: 'overdueDays', field: 'overdue_days', max: 3650, fractionDigits: 0 },
  { key: 'bkiRequests', field: 'bki_requests', max: 100, fractionDigits: 0 },
  { key: 'taxDebt', field: 'tax_debt', max: 1_000_000_000, fractionDigits: 0 },
  { key: 'participants', field: 'participants', max: 10, fractionDigits: 0 },
  { key: 'contractPrice', field: 'contract_price', max: 10_000_000_000, fractionDigits: 0 },
] as const

const props = defineProps<{
  // Правка своей компании: id её создателя
  personaId?: string
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()
const { enterCabinet } = useSession()

const options = ref<Nullable<SandboxPersonaOptionsInterface>>(null)
const isOptionsLoading = ref(false)
const optionsError = ref(false)
const isSubmitting = ref(false)
const isLoggingIn = ref(false)
const isSubmitted = ref(false)
const innServerError = ref<Nullable<string>>(null)
const highlightedFields = ref<string[]>([])
const readyGroup = ref<Nullable<SandboxPersonaGroupInterface>>(null)
const previewRef = useTemplateRef<HTMLElement>('preview')

const form = reactive<SandboxPersonaFormInterface>({
  fullName: '',
  organization: '',
  form: LegalFormEnum.Llc,
  industry: null,
  structure: null,
  accountant: false,
  representative: false,
  seasonality: null,
  stability: null,
  trend: null,
  channel: null,
  loans: null,
  delays: null,
  ageMonths: 36,
  headcount: 12,
  inflowAvg: 3_000_000,
  flags: [],
  inn: '',
  inflowCv: null,
  inflowTrend: null,
  debtLoad: null,
  overdueDays: null,
  bkiRequests: null,
  taxDebt: null,
  participants: null,
  profitMargin: null,
  contractPrice: null,
})

const isEdit = computed(() => Boolean(props.personaId))
const isBusy = computed(() => isSubmitting.value || isLoggingIn.value)

// Правка своей компании сразу открывает результат: ответы уже есть
const stage = ref<BuilderStage>(props.personaId ? 'result' : 'interview')
const question = ref(1)
const selectedRevenue = ref<Nullable<string>>(null)
const selectedTeam = ref<Nullable<string>>(null)

// Банк считает, когда вопросы загружены и ответы на месте: при правке — уже восстановленные
const { preview, conflict, isLoading: isPreviewLoading, error: previewError, loadPreview } =
  useSandboxPersonaPreview(() => form, () => props.personaId ?? null, () => stage.value === 'result' && Boolean(options.value))

const industryOptions = computed(() => options.value?.industries ?? [])

const applicableStructures = computed(() =>
  (options.value?.structures ?? []).filter((structure) => structure.forms.includes(form.form)),
)

const applicablePeople = computed(() =>
  (options.value?.people ?? []).filter((person) => person.forms.includes(form.form)),
)

const accountantOption = computed(() => options.value?.people.find((person) => person.id === 'accountant') ?? null)

const representativeOption = computed(() =>
  applicablePeople.value.find((person) => person.id === 'representative') ?? null,
)

const monthsSuffix = computed(() => ` ${t('sandbox.builder.fields.monthsShort')}`)

const submitLabel = computed(() => (isEdit.value ? t('sandbox.builder.save') : t('sandbox.builder.create')))

const highlightedFlagIds = computed(() =>
  highlightedFields.value
    .filter((field) => field.startsWith('flags.'))
    .map((field) => field.slice('flags.'.length)),
)

const applicableFlags = computed(() =>
  (options.value?.flags ?? []).filter((flag) => flag.forms.includes(form.form)),
)

// Просрочка бывает только по кредиту: без кредитов вопрос не показываем
const isDelaysVisible = computed(() => form.loans !== 'none')

// Имя и название необязательны: бэкенд придумает их сам («ООО «Кофейня 7»»)
const errors = computed(() => {
  const result: Partial<Record<'inn', string>> = {}

  if (!isSubmitted.value) return innServerError.value ? { inn: innServerError.value } : result

  if (innServerError.value) {
    result.inn = innServerError.value
  } else if (form.inn.trim() && !INN_PATTERN.test(form.inn.trim())) {
    result.inn = t('sandbox.builder.innInvalid')
  }

  return result
})

function isHighlighted(...keys: string[]) {
  return keys.some((key) => highlightedFields.value.includes(key))
}

// Противоречие ответов показываем у тех полей, которые оно называет
function conflictFor(...keys: string[]) {
  return conflict.value && keys.some((key) => conflict.value?.fields.includes(key)) ? conflict.value.message : null
}

// На мобильном предпросмотр под формой: полоса снизу возвращает к нему одним касанием
function scrollToPreview() {
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  previewRef.value?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth', block: 'start' })
}

function handleHighlight(fields: string[]) {
  highlightedFields.value = fields
}

function handleFlagsChange(flags: string[]) {
  form.flags = flags
}

// ── Сохранённые ответы: бэкенд отдаёт карточку, а не ответы конструктора, поэтому правку берём из памяти браузера ──

function readSavedAnswers(): Record<string, SandboxPersonaFormInterface> {
  try {
    return JSON.parse(localStorage.getItem(ANSWERS_STORAGE_KEY) ?? '{}') as Record<string, SandboxPersonaFormInterface>
  } catch {
    return {}
  }
}

function saveAnswers(personaId: string) {
  try {
    localStorage.setItem(
      ANSWERS_STORAGE_KEY,
      JSON.stringify({ ...readSavedAnswers(), [personaId]: { ...form } }),
    )
  } catch {
    // Хранилище недоступно (приватный режим) — правка начнётся с ответов по умолчанию
  }
}

// ── Загрузка вопросов ──

function applyDefaults(loaded: SandboxPersonaOptionsInterface) {
  const numberDefault = (id: string, fallback: number) => {
    const value = loaded.params.find((param) => param.id === id)?.defaultValue

    return typeof value === 'number' ? value : fallback
  }

  form.ageMonths = numberDefault('age_months', 36)
  form.headcount = numberDefault('headcount', 12)
  form.inflowAvg = numberDefault('inflow_avg', 3_000_000)

  // Отрасль без значения по умолчанию: её выбирает человек первым вопросом. Остальное — отправная точка
  form.structure = applicableStructures.value[0]?.id ?? null
  form.stability = loaded.choices.stability[0]?.id ?? null
  form.trend = loaded.choices.trend[0]?.id ?? null
  form.loans = loaded.choices.loans[0]?.id ?? null
  form.delays = loaded.choices.delays[0]?.id ?? null
}

async function restoreForEdit() {
  if (!props.personaId) return

  const saved = readSavedAnswers()[props.personaId]

  if (saved) {
    Object.assign(form, saved)

    return
  }

  // Сохранённых ответов нет (компанию создали не здесь): подставляем хотя бы имя и название
  try {
    const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)
    const persona = data.data.find((item) => item.id === props.personaId)

    if (persona) {
      form.fullName = persona.full_name
      form.organization = persona.organization
    }
  } catch (err: unknown) {
    console.error('Sandbox persona loading for edit failed:', err)
  }
}

async function loadOptions() {
  if (isOptionsLoading.value) return

  isOptionsLoading.value = true
  optionsError.value = false

  try {
    const { data } = await sandboxService.fetchPersonaOptions($fetch, locale.value as AppLocale)
    const isFirstLoad = !options.value

    options.value = SandboxPersonaOptionsMapper.toEntity(data.data)

    // При смене языка ответы человека сохраняем
    if (isFirstLoad) {
      applyDefaults(options.value)
      await restoreForEdit()
    }
  } catch (err: unknown) {
    console.error('Sandbox persona options loading failed:', err)
    optionsError.value = true
  } finally {
    isOptionsLoading.value = false
  }
}

// ── Зависимости между ответами ──

function applyIndustryDefaults() {
  const industry = industryOptions.value.find((item) => item.id === form.industry)

  if (!industry) return

  form.seasonality = industry.seasonality
  form.channel = industry.channel
}

function syncWithForm() {
  const structures = applicableStructures.value

  if (!structures.some((structure) => structure.id === form.structure)) {
    form.structure = structures[0]?.id ?? null
  }

  if (!applicablePeople.value.some((person) => person.id === 'representative')) form.representative = false

  form.flags = form.flags.filter((flag) => applicableFlags.value.some((item) => item.id === flag))
}

function syncDelaysWithLoans() {
  if (form.loans === 'none') form.delays = 'none'
}

// ── Отправка ──

function applyServerError(err: unknown): boolean {
  const problem = getApiProblem(err)

  if (!problem) return false

  if (problem.code === ApiErrorCodeEnum.InnInvalid) {
    const suggested = typeof problem.suggested_inn === 'string' ? problem.suggested_inn : ''

    innServerError.value = suggested
      ? t('sandbox.builder.innSuggested', { inn: suggested })
      : t('sandbox.builder.innInvalid')

    return true
  }

  if (problem.code === ApiErrorCodeEnum.InnTaken) {
    innServerError.value = t('sandbox.builder.innTaken')

    return true
  }

  return false
}

async function loadReadyGroup(companyInn: string) {
  const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)
  const personas = data.data
    .map((persona) => SandboxMapper.toEntity(persona))
    .filter((persona) => persona.companyInn === companyInn)

  readyGroup.value = {
    key: companyInn,
    title: personas[0]?.companyName ?? null,
    isBank: false,
    ownerId: null,
    personas,
  }
}

async function submit() {
  isSubmitted.value = true
  innServerError.value = null

  if (Object.keys(errors.value).length || conflict.value || isBusy.value) return

  isSubmitting.value = true

  try {
    const payload = SandboxMapper.toPayload(form)
    const { data } = props.personaId
      ? await sandboxService.updatePersona($fetch, props.personaId, payload)
      : await sandboxService.createPersona($fetch, payload)

    saveAnswers(data.data.id)
    await loadReadyGroup(data.data.company_inn ?? data.data.inn)
  } catch (err: unknown) {
    console.error('Sandbox company saving failed:', err)

    if (applyServerError(err)) return

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: getApiProblem(err)?.detail ?? t('toast.sandboxCreateError'),
      life: 5000,
    })
  } finally {
    isSubmitting.value = false
  }
}

async function loginAsPersona(persona: SandboxPersonaInterface) {
  if (isLoggingIn.value) return

  isLoggingIn.value = true

  try {
    await enterCabinet(persona.id)
  } catch (err: unknown) {
    console.error('Sandbox login failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.loginError'),
      life: 4000,
    })
  } finally {
    isLoggingIn.value = false
  }
}

function backToForm() {
  readyGroup.value = null
}

// ── Интервью: три вопроса, каждый ответ — сразу следующий шаг ──

function chooseIndustry(industryId: string) {
  form.industry = industryId
  question.value = 2
}

function chooseRevenue(range: RevenueRange) {
  form.inflowAvg = range.value
  selectedRevenue.value = range.id
  question.value = 3
}

// Третий ответ — и сразу результат: что скажет банк
function chooseTeam(option: TeamOption) {
  selectedTeam.value = option.id
  form.form = option.form
  form.structure = option.structure

  if (option.form === LegalFormEnum.SoleProprietor) form.representative = false

  stage.value = 'result'
}

function goBackInInterview() {
  if (question.value > 1) {
    question.value--
  } else {
    router.push({ name: 'login' })
  }
}

function restartInterview() {
  question.value = 1
  stage.value = 'interview'
}

function cancelBuilding() {
  router.push({ name: 'login' })
}

watch(() => form.form, syncWithForm)
watch(() => form.industry, applyIndustryDefaults)
watch(() => form.loans, syncDelaysWithLoans)
watch(() => form.inn, () => {
  innServerError.value = null
})
watch(locale, loadOptions)
onMounted(loadOptions)
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile />
    </AppHeader>

    <main class="mx-auto flex max-w-[1600px] flex-col gap-8 px-4 py-8 sm:px-6 sm:py-10">
      <div class="max-w-2xl">
        <RouterLink
          :to="{ name: 'login' }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('sandbox.builder.back') }}
        </RouterLink>

        <h1 class="mt-4 text-3xl font-bold tracking-tight text-fino-text sm:text-4xl">
          {{ isEdit ? t('sandbox.builder.editTitle') : t('sandbox.builder.title') }}
        </h1>

        <p class="mt-3 text-sm leading-relaxed text-fino-text-muted sm:text-base">
          {{ stage === 'interview' ? t('sandbox.builder.interview.description') : t('sandbox.builder.description') }}
        </p>
      </div>

      <!-- Компания готова: люди, под которыми можно войти -->
      <section
        v-if="readyGroup"
        class="flex flex-col gap-6"
      >
        <div class="flex flex-col gap-1 rounded-3xl border border-green-500/30 bg-green-500/5 p-5">
          <p class="flex items-center gap-2 text-base font-bold text-fino-text">
            <i
              class="pi pi-check-circle text-green-600 dark:text-green-400"
              aria-hidden="true"
            />
            {{ t('sandbox.builder.ready.title') }}
          </p>

          <p class="text-sm text-fino-text-muted">
            {{ t('sandbox.builder.ready.text') }}
          </p>
        </div>

        <SandboxPersonaGroup
          :group="readyGroup"
          :is-busy="isLoggingIn"
          @login="loginAsPersona"
        />

        <div>
          <button
            type="button"
            class="cursor-pointer rounded-xl border border-fino-border bg-fino-surface px-5 py-3 text-sm font-semibold
                   text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
            @click="backToForm"
          >
            {{ t('sandbox.builder.ready.edit') }}
          </button>
        </div>
      </section>

      <SandboxPersonaBuilderSkeleton
        v-else-if="isOptionsLoading && !options"
        :is-result="stage === 'result'"
      />

      <AppErrorState
        v-else-if="optionsError"
        :message="t('sandbox.builder.optionsLoadError')"
        @retry="loadOptions"
      />

      <!-- Интервью: три вопроса до первого результата -->
      <section
        v-else-if="options && stage === 'interview'"
        class="flex max-w-4xl flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-8"
        :aria-label="t('sandbox.builder.interview.label')"
      >
        <div class="flex items-center justify-between gap-3">
          <p class="text-sm font-semibold text-fino-text-muted">
            {{ t('sandbox.builder.interview.progress', { current: question, total: INTERVIEW_QUESTIONS }) }}
          </p>

          <ol
            class="flex gap-1.5"
            aria-hidden="true"
          >
            <li
              v-for="step in INTERVIEW_QUESTIONS"
              :key="step"
              class="h-1.5 w-8 rounded-full transition-colors duration-300 motion-reduce:transition-none"
              :class="step <= question ? 'bg-primary' : 'bg-fino-surface-secondary'"
            />
          </ol>
        </div>

        <!-- 1. Чем занимаетесь — без значения по умолчанию -->
        <div
          v-if="question === 1"
          class="flex flex-col gap-4"
        >
          <h2 class="text-xl font-bold tracking-tight text-fino-text sm:text-2xl">
            {{ t('sandbox.builder.interview.industry') }}
          </h2>

          <ul class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
            <li
              v-for="industry in industryOptions"
              :key="industry.id"
            >
              <button
                type="button"
                class="flex h-full min-h-14 w-full cursor-pointer items-center rounded-2xl border px-4 py-3 text-left text-sm
                       font-semibold text-fino-text transition-colors duration-200 hover:border-primary hover:bg-fino-accent
                       focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
                :class="form.industry === industry.id ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                :aria-pressed="form.industry === industry.id"
                @click="chooseIndustry(industry.id)"
              >
                {{ industry.title }}
              </button>
            </li>
          </ul>
        </div>

        <!-- 2. Сколько приходит на счёт — диапазонами -->
        <div
          v-else-if="question === 2"
          class="flex flex-col gap-4"
        >
          <h2 class="text-xl font-bold tracking-tight text-fino-text sm:text-2xl">
            {{ t('sandbox.builder.interview.revenue') }}
          </h2>

          <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <li
              v-for="range in REVENUE_RANGES"
              :key="range.id"
            >
              <button
                type="button"
                class="flex min-h-16 w-full cursor-pointer items-center rounded-2xl border px-5 py-4 text-left text-base
                       font-bold text-fino-text transition-colors duration-200 hover:border-primary hover:bg-fino-accent
                       focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
                :class="selectedRevenue === range.id ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                :aria-pressed="selectedRevenue === range.id"
                @click="chooseRevenue(range)"
              >
                {{ t(`sandbox.builder.interview.revenueRanges.${range.id}`) }}
              </button>
            </li>
          </ul>
        </div>

        <!-- 3. Кто в компании — карточки словами человека; бухгалтер и доверенность — по желанию -->
        <div
          v-else
          class="flex flex-col gap-4"
        >
          <h2 class="text-xl font-bold tracking-tight text-fino-text sm:text-2xl">
            {{ t('sandbox.builder.interview.team') }}
          </h2>

          <!-- По желанию: бухгалтер и представитель — переключатели до выбора карточки -->
          <div class="flex flex-wrap items-center gap-2 text-sm">
            <span class="mr-1 font-semibold text-fino-text-muted">{{ t('sandbox.builder.interview.also') }}</span>

            <label
              class="inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-fino-text
                     transition-colors duration-200 hover:border-primary motion-reduce:transition-none"
              :class="form.accountant ? 'border-primary bg-fino-accent' : 'border-fino-border bg-fino-surface'"
            >
              <Checkbox
                v-model="form.accountant"
                binary
              />
              {{ t('sandbox.builder.interview.accountant') }}
            </label>

            <label
              class="inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-fino-text
                     transition-colors duration-200 hover:border-primary motion-reduce:transition-none"
              :class="form.representative ? 'border-primary bg-fino-accent' : 'border-fino-border bg-fino-surface'"
            >
              <Checkbox
                v-model="form.representative"
                binary
              />
              {{ t('sandbox.builder.interview.representative') }}
            </label>
          </div>

          <ul class="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <li
              v-for="option in TEAM_OPTIONS"
              :key="option.id"
            >
              <button
                type="button"
                class="flex h-full w-full cursor-pointer flex-col gap-1 rounded-2xl border px-5 py-4 text-left
                       transition-colors duration-200 hover:border-primary hover:bg-fino-accent
                       focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
                :class="selectedTeam === option.id ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                :aria-pressed="selectedTeam === option.id"
                @click="chooseTeam(option)"
              >
                <span class="text-base font-bold text-fino-text">{{ t(`sandbox.builder.interview.teams.${option.id}.title`) }}</span>
                <span class="text-sm text-fino-text-muted">{{ t(`sandbox.builder.interview.teams.${option.id}.hint`) }}</span>
              </button>
            </li>
          </ul>
        </div>

        <button
          type="button"
          class="inline-flex w-fit cursor-pointer items-center gap-2 text-sm font-semibold text-fino-text-muted
                 transition-colors hover:text-fino-text focus-visible:outline-2 focus-visible:outline-primary"
          @click="goBackInInterview"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ question > 1 ? t('sandbox.builder.interview.back') : t('sandbox.builder.cancel') }}
        </button>
      </section>

      <!-- Результат: что скажет банк — и «Уточнить» рядом; каждое изменение пересчитывает предпросмотр -->
      <div
        v-else-if="options"
        class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_28rem]"
      >
        <div
          ref="preview"
          class="min-w-0 scroll-mt-24 lg:sticky lg:top-28"
        >
          <SandboxPersonaPreview
            :preview="preview"
            :is-loading="isPreviewLoading"
            :has-error="previewError"
            :has-representative="form.representative"
            @highlight="handleHighlight"
            @retry="loadPreview"
          />
        </div>

        <!-- Снизу место под полосу предпросмотра и кнопку «Как проверить»: кнопки формы они не закрывают -->
        <form
          class="flex min-w-0 flex-col gap-3 pb-32 lg:pb-16"
          novalidate
          :aria-busy="isSubmitting"
          @submit.prevent="submit"
        >
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-bold tracking-tight text-fino-text">
              {{ t('sandbox.builder.refine.title') }}
            </h2>

            <button
              v-if="!isEdit"
              type="button"
              class="cursor-pointer text-sm font-semibold text-fino-text-muted transition-colors hover:text-primary"
              @click="restartInterview"
            >
              {{ t('sandbox.builder.refine.restart') }}
            </button>
          </div>

          <!-- О компании: имя и название — по желанию -->
          <details class="group rounded-2xl border border-fino-border bg-fino-surface">
            <summary
              class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                     text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t('sandbox.builder.refine.company') }}
              <i
                class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                       group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>

            <div class="grid grid-cols-1 gap-4 px-4 pb-4">
              <SandboxPersonaField
                input-id="persona-fullName"
                :label="t('sandbox.builder.fields.fullName')"
                :error="null"
              >
                <InputText
                  id="persona-fullName"
                  v-model="form.fullName"
                  :maxlength="FULL_NAME_MAX_LENGTH"
                  :placeholder="t('sandbox.builder.fields.optional')"
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>

              <SandboxPersonaField
                input-id="persona-organization"
                :label="t('sandbox.builder.fields.organization')"
                :error="null"
              >
                <InputText
                  id="persona-organization"
                  v-model="form.organization"
                  :placeholder="t('sandbox.builder.fields.organizationAuto')"
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>

              <SandboxPersonaField
                input-id="persona-form"
                :label="t('sandbox.builder.fields.form')"
                :error="null"
              >
                <SelectButton
                  v-model="form.form"
                  :options="options.forms"
                  option-label="title"
                  option-value="id"
                  :allow-empty="false"
                  :disabled="isBusy"
                  :aria-label="t('sandbox.builder.fields.form')"
                />
              </SandboxPersonaField>

              <SandboxPersonaField
                input-id="persona-industry"
                :label="t('sandbox.builder.fields.industry')"
                :error="null"
                :is-highlighted="isHighlighted('industry')"
              >
                <Select
                  v-model="form.industry"
                  input-id="persona-industry"
                  :options="industryOptions"
                  option-label="title"
                  option-value="id"
                  filter
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>

              <SandboxPersonaField
                input-id="persona-inflowAvg"
                :label="t('sandbox.builder.fields.inflowAvg')"
                :error="null"
                :is-highlighted="isHighlighted('inflow_avg')"
              >
                <InputNumber
                  v-model="form.inflowAvg"
                  input-id="persona-inflowAvg"
                  :min="1"
                  :max-fraction-digits="0"
                  suffix=" ₽"
                  :locale="locale"
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>

              <div class="grid grid-cols-2 gap-4">
                <SandboxPersonaField
                  input-id="persona-headcount"
                  :label="t('sandbox.builder.fields.headcount')"
                  :error="null"
                  :is-highlighted="isHighlighted('headcount')"
                >
                  <InputNumber
                    v-model="form.headcount"
                    input-id="persona-headcount"
                    :min="1"
                    :max-fraction-digits="0"
                    :locale="locale"
                    :disabled="isBusy"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  input-id="persona-ageMonths"
                  :label="t('sandbox.builder.fields.ageMonths')"
                  :error="null"
                  :is-highlighted="isHighlighted('age_months', 'flags.young_business')"
                >
                  <InputNumber
                    v-model="form.ageMonths"
                    input-id="persona-ageMonths"
                    :min="1"
                    :max-fraction-digits="0"
                    :suffix="monthsSuffix"
                    :locale="locale"
                    :disabled="isBusy"
                    fluid
                  />
                </SandboxPersonaField>
              </div>
            </div>
          </details>

          <!-- Кто в компании: нормы закона — только во всплывающей «i» -->
          <details
            class="group rounded-2xl border border-fino-border bg-fino-surface"
            :open="Boolean(conflictFor('structure'))"
          >
            <summary
              class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                     text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t('sandbox.builder.refine.team') }}
              <i
                class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                       group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>

            <div class="flex flex-col gap-3 px-4 pb-4">
              <SandboxPersonaField
                v-if="applicableStructures.length"
                input-id="persona-structure"
                :label="t('sandbox.builder.fields.structure')"
                :error="conflictFor('structure')"
                :is-highlighted="isHighlighted('structure')"
              >
                <div
                  class="flex flex-col gap-2"
                  role="radiogroup"
                  :aria-label="t('sandbox.builder.fields.structure')"
                >
                  <label
                    v-for="structure in applicableStructures"
                    :key="structure.id"
                    class="flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors
                           duration-200 hover:bg-fino-surface-hover motion-reduce:transition-none"
                    :class="form.structure === structure.id ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                  >
                    <RadioButton
                      v-model="form.structure"
                      :value="structure.id"
                      name="persona-structure"
                      :disabled="isBusy"
                      class="shrink-0"
                    />

                    <span class="min-w-0 flex-1 break-words text-sm font-semibold text-fino-text">{{ structure.title }}</span>

                    <i
                      class="pi pi-info-circle shrink-0 text-xs text-fino-text-muted"
                      :title="structure.means"
                      :aria-label="structure.means"
                    />
                  </label>
                </div>
              </SandboxPersonaField>

              <label
                v-if="accountantOption"
                class="flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors duration-200
                       hover:bg-fino-surface-hover motion-reduce:transition-none"
                :class="form.accountant ? 'border-primary bg-fino-accent' : 'border-fino-border'"
              >
                <Checkbox
                  v-model="form.accountant"
                  binary
                  :disabled="isBusy"
                  class="shrink-0"
                />
                <span class="min-w-0 flex-1 text-sm font-semibold text-fino-text">{{ t('sandbox.builder.interview.accountant') }}</span>
                <i
                  class="pi pi-info-circle shrink-0 text-xs text-fino-text-muted"
                  :title="accountantOption.means"
                  :aria-label="accountantOption.means"
                />
              </label>

              <label
                v-if="representativeOption"
                class="flex cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors duration-200
                       hover:bg-fino-surface-hover motion-reduce:transition-none"
                :class="form.representative ? 'border-primary bg-fino-accent' : 'border-fino-border'"
              >
                <Checkbox
                  v-model="form.representative"
                  binary
                  :disabled="isBusy"
                  class="shrink-0"
                />
                <span class="min-w-0 flex-1 text-sm font-semibold text-fino-text">{{ t('sandbox.builder.interview.representative') }}</span>
                <i
                  class="pi pi-info-circle shrink-0 text-xs text-fino-text-muted"
                  :title="representativeOption.means"
                  :aria-label="representativeOption.means"
                />
              </label>
            </div>
          </details>

          <!-- Деньги: сезонность, ровность, тренд, канал, кредиты, просрочки -->
          <details class="group rounded-2xl border border-fino-border bg-fino-surface">
            <summary
              class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                     text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t('sandbox.builder.refine.money') }}
              <i
                class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                       group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>

            <div class="flex flex-col gap-4 px-4 pb-4">
              <template
                v-for="field in CHOICE_FIELDS"
                :key="field"
              >
                <SandboxPersonaField
                  v-if="field !== 'delays' || isDelaysVisible"
                  :input-id="`persona-${field}`"
                  :label="t(`sandbox.builder.fields.${field}`)"
                  :error="conflictFor(field)"
                  :is-highlighted="isHighlighted(field)"
                >
                  <SandboxPersonaChoice
                    v-model="form[field]"
                    :options="options.choices[field]"
                    :label="t(`sandbox.builder.fields.${field}`)"
                    :is-disabled="isBusy"
                  />
                </SandboxPersonaField>
              </template>
            </div>
          </details>

          <!-- Особенности: факты о компании, без исхода -->
          <details class="group rounded-2xl border border-fino-border bg-fino-surface">
            <summary
              class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                     text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t('sandbox.builder.flagsTitle') }}
              <i
                class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                       group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>

            <div class="px-4 pb-4">
              <p
                v-if="conflictFor('flags.large_deal')"
                class="mb-3 text-sm text-red-600 dark:text-red-400"
              >
                {{ conflictFor('flags.large_deal') }}
              </p>

              <SandboxPersonaFlagsPicker
                :groups="options.groups"
                :flags="applicableFlags"
                :selected="form.flags"
                :is-disabled="isBusy"
                :highlighted="highlightedFlagIds"
                @change="handleFlagsChange"
              />
            </div>
          </details>

          <!-- Точные цифры: пустые бэкенд выведет из ответов выше -->
          <details class="group rounded-2xl border border-fino-border bg-fino-surface">
            <summary
              class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                     text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
            >
              {{ t('sandbox.builder.exactTitle') }}
              <i
                class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                       group-open:rotate-180 motion-reduce:transition-none"
                aria-hidden="true"
              />
            </summary>

            <div class="grid grid-cols-1 gap-4 px-4 pb-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
              <SandboxPersonaField
                input-id="persona-inn"
                :label="t('sandbox.builder.fields.inn')"
                :hint="t('sandbox.builder.fields.innHint')"
                :error="errors.inn ?? null"
              >
                <InputText
                  id="persona-inn"
                  v-model="form.inn"
                  inputmode="numeric"
                  :maxlength="12"
                  :invalid="Boolean(errors.inn)"
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>

              <SandboxPersonaField
                v-for="field in EXACT_FIELDS"
                :key="field.key"
                :input-id="`persona-${field.key}`"
                :label="t(`sandbox.builder.exact.${field.key}`)"
                :error="null"
                :is-highlighted="isHighlighted(field.field)"
              >
                <InputNumber
                  v-model="form[field.key]"
                  :input-id="`persona-${field.key}`"
                  :min="0"
                  :max="field.max"
                  :max-fraction-digits="field.fractionDigits"
                  :locale="locale"
                  :placeholder="t('sandbox.builder.exactAuto')"
                  :disabled="isBusy"
                  fluid
                />
              </SandboxPersonaField>
            </div>
          </details>

          <div class="mt-2 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end lg:flex-col-reverse xl:flex-row">
            <button
              type="button"
              class="inline-flex min-h-12 cursor-pointer items-center justify-center rounded-xl border border-fino-border
                     bg-fino-surface px-5 py-3 text-sm font-semibold text-fino-text transition-colors duration-200
                     hover:bg-fino-surface-hover disabled:cursor-not-allowed disabled:opacity-60
                     motion-reduce:transition-none"
              :disabled="isBusy"
              @click="cancelBuilding"
            >
              {{ t('sandbox.builder.cancel') }}
            </button>

            <button
              type="submit"
              class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-6 py-3
                     text-sm font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90
                     active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none"
              :disabled="isBusy"
            >
              {{ submitLabel }}
              <i
                class="pi pi-arrow-right text-xs"
                aria-hidden="true"
              />
            </button>
          </div>
        </form>
      </div>

      <SandboxPersonaPreviewBar
        v-if="!readyGroup && stage === 'result'"
        :preview="preview"
        :is-loading="isPreviewLoading"
        @show="scrollToPreview"
      />
    </main>
  </div>
</template>
