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

const { preview, conflict, isLoading: isPreviewLoading, error: previewError, loadPreview } =
  useSandboxPersonaPreview(() => form, () => props.personaId ?? null)

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

const errors = computed(() => {
  const required = t('sandbox.builder.required')
  const result: Partial<Record<'fullName' | 'organization' | 'inn', string>> = {}

  if (!isSubmitted.value) return innServerError.value ? { inn: innServerError.value } : result

  if (!form.fullName.trim()) result.fullName = required
  if (!form.organization.trim()) result.organization = required

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

  // Первая отрасль и первые ответы — отправная точка: человек правит то, что отличается
  form.industry = loaded.industries[0]?.id ?? null
  applyIndustryDefaults()
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
          {{ t('sandbox.builder.description') }}
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

      <div
        v-else
        class="grid grid-cols-1 items-start gap-6 lg:grid-cols-[minmax(0,1fr)_24rem] xl:grid-cols-[minmax(0,1fr)_28rem]"
      >
        <form
          class="flex min-w-0 flex-col gap-6"
          novalidate
          :aria-busy="isOptionsLoading || isSubmitting"
          @submit.prevent="submit"
        >
          <SandboxPersonaBuilderSkeleton v-if="isOptionsLoading && !options" />

          <AppErrorState
            v-else-if="optionsError"
            :message="t('sandbox.builder.optionsLoadError')"
            @retry="loadOptions"
          />

          <template v-else-if="options">
            <!-- 1. Кто вы -->
            <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
              <h2 class="flex items-center gap-3 text-lg font-bold tracking-tight text-fino-text">
                <span class="flex size-8 items-center justify-center rounded-full bg-primary text-sm text-primary-contrast">1</span>
                {{ t('sandbox.builder.steps.who') }}
              </h2>

              <div class="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2">
                <SandboxPersonaField
                  input-id="persona-fullName"
                  :label="t('sandbox.builder.fields.fullName')"
                  :error="errors.fullName ?? null"
                >
                  <InputText
                    id="persona-fullName"
                    v-model="form.fullName"
                    :maxlength="FULL_NAME_MAX_LENGTH"
                    :placeholder="t('sandbox.builder.fields.fullNamePlaceholder')"
                    :invalid="Boolean(errors.fullName)"
                    :disabled="isBusy"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  input-id="persona-organization"
                  :label="t('sandbox.builder.fields.organization')"
                  :error="errors.organization ?? null"
                >
                  <InputText
                    id="persona-organization"
                    v-model="form.organization"
                    :placeholder="t('sandbox.builder.fields.organizationPlaceholder')"
                    :invalid="Boolean(errors.organization)"
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
                  >
                    <template #option="{ option }">
                      <div class="flex min-w-0 flex-col">
                        <span class="break-words">{{ option.title }}</span>
                        <span class="text-xs text-fino-text-muted">{{ option.okved }}</span>
                      </div>
                    </template>
                  </Select>
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
            </section>

            <!-- 2. Как устроена компания -->
            <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
              <h2 class="flex items-center gap-3 text-lg font-bold tracking-tight text-fino-text">
                <span class="flex size-8 items-center justify-center rounded-full bg-primary text-sm text-primary-contrast">2</span>
                {{ t('sandbox.builder.steps.structure') }}
              </h2>

              <div class="mt-5 flex flex-col gap-5">
                <SandboxPersonaField
                  v-if="applicableStructures.length"
                  input-id="persona-structure"
                  :label="t('sandbox.builder.fields.structure')"
                  :error="conflictFor('structure')"
                  :is-highlighted="isHighlighted('structure')"
                >
                  <div
                    class="grid grid-cols-1 gap-2 md:grid-cols-2"
                    role="radiogroup"
                    :aria-label="t('sandbox.builder.fields.structure')"
                  >
                    <label
                      v-for="structure in applicableStructures"
                      :key="structure.id"
                      class="flex cursor-pointer items-start gap-3 rounded-2xl border p-3 transition-colors duration-200
                             hover:bg-fino-surface-hover motion-reduce:transition-none"
                      :class="form.structure === structure.id ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                    >
                      <RadioButton
                        v-model="form.structure"
                        :value="structure.id"
                        name="persona-structure"
                        :disabled="isBusy"
                        class="mt-0.5 shrink-0"
                      />

                      <span class="min-w-0">
                        <span class="block break-words text-sm font-semibold text-fino-text">{{ structure.title }}</span>
                        <span class="mt-0.5 block break-words text-xs leading-relaxed text-fino-text-muted">{{ structure.means }}</span>
                      </span>
                    </label>
                  </div>
                </SandboxPersonaField>

                <ul class="grid grid-cols-1 gap-2 md:grid-cols-2">
                  <li v-if="accountantOption">
                    <label
                      class="flex h-full cursor-pointer items-start gap-3 rounded-2xl border p-3 transition-colors duration-200
                             hover:bg-fino-surface-hover motion-reduce:transition-none"
                      :class="form.accountant ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                    >
                      <Checkbox
                        v-model="form.accountant"
                        binary
                        :disabled="isBusy"
                        class="mt-0.5 shrink-0"
                      />

                      <span class="min-w-0">
                        <span class="block break-words text-sm font-semibold text-fino-text">
                          {{ accountantOption?.title }}
                        </span>
                        <span class="mt-0.5 block break-words text-xs leading-relaxed text-fino-text-muted">
                          {{ accountantOption?.means }}
                        </span>
                      </span>
                    </label>
                  </li>

                  <li v-if="representativeOption">
                    <label
                      class="flex h-full cursor-pointer items-start gap-3 rounded-2xl border p-3 transition-colors duration-200
                             hover:bg-fino-surface-hover motion-reduce:transition-none"
                      :class="form.representative ? 'border-primary bg-fino-accent' : 'border-fino-border'"
                    >
                      <Checkbox
                        v-model="form.representative"
                        binary
                        :disabled="isBusy"
                        class="mt-0.5 shrink-0"
                      />

                      <span class="min-w-0">
                        <span class="block break-words text-sm font-semibold text-fino-text">
                          {{ representativeOption?.title }}
                        </span>
                        <span class="mt-0.5 block break-words text-xs leading-relaxed text-fino-text-muted">
                          {{ representativeOption?.means }}
                        </span>
                      </span>
                    </label>
                  </li>
                </ul>
              </div>
            </section>

            <!-- 3. Деньги -->
            <section class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6">
              <h2 class="flex items-center gap-3 text-lg font-bold tracking-tight text-fino-text">
                <span class="flex size-8 items-center justify-center rounded-full bg-primary text-sm text-primary-contrast">3</span>
                {{ t('sandbox.builder.steps.money') }}
              </h2>

              <div class="mt-5 flex flex-col gap-5">
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

                <!-- Особенности: факты о компании, без исхода -->
                <details class="group rounded-2xl border border-fino-border">
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
                <details class="group rounded-2xl border border-fino-border">
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

                  <div class="grid grid-cols-1 gap-5 px-4 pb-4 sm:grid-cols-2">
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
              </div>
            </section>

            <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
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
          </template>
        </form>

        <!-- Живой предпросмотр: что банк скажет и почему -->
        <div
          ref="preview"
          class="min-w-0 scroll-mt-24 pb-20 lg:sticky lg:top-28 lg:pb-0"
        >
          <SandboxPersonaPreview
            :preview="preview"
            :is-loading="isPreviewLoading"
            :has-error="previewError"
            @highlight="handleHighlight"
            @retry="loadPreview"
          />
        </div>
      </div>

      <SandboxPersonaPreviewBar
        v-if="!readyGroup"
        :preview="preview"
        :is-loading="isPreviewLoading"
        @show="scrollToPreview"
      />
    </main>
  </div>
</template>
