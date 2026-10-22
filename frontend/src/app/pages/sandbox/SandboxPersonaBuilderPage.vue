<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Button from 'primevue/button'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import SelectButton from 'primevue/selectbutton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import SandboxPersonaBuilderPromo from '@/app/features/sandbox/components/SandboxPersonaBuilderPromo.vue'
import SandboxPersonaBuilderSkeleton from '@/app/features/sandbox/components/SandboxPersonaBuilderSkeleton.vue'
import SandboxDemoBadge from '@/app/features/sandbox/components/SandboxDemoBadge.vue'
import SandboxPersonaField from '@/app/features/sandbox/components/SandboxPersonaField.vue'
import SandboxPersonaFlagsPicker from '@/app/features/sandbox/components/SandboxPersonaFlagsPicker.vue'
import { getApiErrorCode, getApiProblem, useApiFetch } from '@/app/composables/useApiFetch'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaOptionsMapper } from '@/app/mappers/sandbox-persona-options.mapper'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'
import { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaFormInterface } from '@/app/types/sandbox/sandbox-persona-form-interface'
import type { SandboxPersonaOptionsInterface } from '@/app/types/sandbox/sandbox-persona-options-interface'

type NumberFieldKey =
  | 'ageMonths' | 'headcount' | 'inflowAvg' | 'inflowCv' | 'inflowTrend' | 'debtLoad'
  | 'overdueDays' | 'bkiRequests' | 'taxDebt' | 'participants' | 'profitMargin' | 'contractPrice'

type FormErrorKey = 'fullName' | 'inn' | 'okved' | 'okvedName' | NumberFieldKey

interface NumberFieldInterface {
  // id параметра в GET v1/sandbox/persona-options: оттуда берутся значение по умолчанию и границы
  paramId: string
  key: NumberFieldKey
  fractionDigits: number
  unit?: 'months' | 'people' | 'rub' | 'days'
  forms?: LegalFormEnum[]
}

// Те же ограничения, что у бэкенда (PersonaIn)
const FULL_NAME_MAX_LENGTH = 120
const ORGANIZATION_MAX_LENGTH = 200
const OKVED_MAX_LENGTH = 8
const OKVED_NAME_MAX_LENGTH = 300
const INN_PATTERN = /^(\d{10}|\d{12})$/
const OKVED_PATTERN = /^\d{2}(\.\d{1,2}){0,2}$/
const IP_INN_LENGTH = 12
const LEGAL_INN_LENGTH = 10

const NUMBER_FIELDS: NumberFieldInterface[] = [
  { paramId: 'participants', key: 'participants', fractionDigits: 0, forms: [LegalFormEnum.Llc] },
  { paramId: 'age_months', key: 'ageMonths', fractionDigits: 0, unit: 'months' },
  { paramId: 'headcount', key: 'headcount', fractionDigits: 0, unit: 'people' },
  { paramId: 'inflow_avg', key: 'inflowAvg', fractionDigits: 0, unit: 'rub' },
  { paramId: 'inflow_cv', key: 'inflowCv', fractionDigits: 2 },
  { paramId: 'inflow_trend', key: 'inflowTrend', fractionDigits: 2 },
  { paramId: 'debt_load', key: 'debtLoad', fractionDigits: 2 },
  { paramId: 'overdue_days', key: 'overdueDays', fractionDigits: 0, unit: 'days' },
  { paramId: 'bki_requests', key: 'bkiRequests', fractionDigits: 0 },
  { paramId: 'tax_debt', key: 'taxDebt', fractionDigits: 0, unit: 'rub' },
  { paramId: 'profit_margin', key: 'profitMargin', fractionDigits: 2 },
  { paramId: 'contract_price', key: 'contractPrice', fractionDigits: 0, unit: 'rub' },
]

const { t, locale } = useI18n({ useScope: 'global' })
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()

const options = ref<Nullable<SandboxPersonaOptionsInterface>>(null)
const isOptionsLoading = ref(false)
const optionsError = ref(false)

const form = reactive<SandboxPersonaFormInterface>({
  fullName: '',
  inn: '',
  organization: '',
  form: LegalFormEnum.Llc,
  okved: '',
  okvedName: '',
  ageMonths: null,
  headcount: null,
  inflowAvg: null,
  inflowCv: null,
  inflowTrend: null,
  debtLoad: null,
  overdueDays: null,
  bkiRequests: null,
  taxDebt: null,
  participants: null,
  profitMargin: null,
  contractPrice: null,
  flags: [],
})

const isSubmitting = ref(false)
const isSubmitted = ref(false)
// Ошибки, которые вернул бэкенд: ИНН (контрольная цифра, занят) и «такой компании не бывает»
const innServerError = ref<Nullable<string>>(null)
const personaServerError = ref<Nullable<string>>(null)

const isOptionsReady = computed(() => Boolean(options.value))

const formOptions = computed(() => options.value?.forms ?? [])

// Флаги, применимые к выбранной форме: остальные бэкенд отклонит (FLAG_NOT_APPLICABLE)
const availableFlags = computed(() =>
  (options.value?.flags ?? []).filter((flag) => flag.forms.includes(form.form)),
)

const numberFields = computed(() =>
  NUMBER_FIELDS
    .filter((field) => !field.forms || field.forms.includes(form.form))
    .map((field) => {
      const param = options.value?.params.find((item) => item.id === field.paramId)

      return {
        ...field,
        min: param?.min ?? undefined,
        max: param?.max ?? undefined,
        // Параметр без значения по умолчанию на бэкенде необязателен (госконтракт)
        isRequired: param ? param.defaultValue !== null : true,
        label: t(`sandbox.builder.params.${field.paramId}.label`),
        hint: t(`sandbox.builder.params.${field.paramId}.hint`),
        suffix: field.unit ? t(`sandbox.builder.units.${field.unit}`) : undefined,
      }
    }),
)

function getErrors(): Partial<Record<FormErrorKey, string>> {
  const errors: Partial<Record<FormErrorKey, string>> = {}
  const required = t('sandbox.builder.required')
  const inn = form.inn.trim()

  if (!form.fullName.trim()) {
    errors.fullName = required
  } else if (form.fullName.trim().split(/\s+/).length < 2) {
    errors.fullName = t('sandbox.builder.fullNameInvalid')
  }

  // ИНН необязателен: пустой бэкенд сгенерирует сам
  if (inn && !INN_PATTERN.test(inn)) {
    errors.inn = t('sandbox.builder.innInvalid')
  } else if (inn && (inn.length === IP_INN_LENGTH) !== (form.form === LegalFormEnum.SoleProprietor)) {
    errors.inn = t('sandbox.builder.innFormMismatch')
  } else if (innServerError.value) {
    errors.inn = innServerError.value
  }

  if (!form.okved.trim()) {
    errors.okved = required
  } else if (!OKVED_PATTERN.test(form.okved.trim())) {
    errors.okved = t('sandbox.builder.okvedInvalid')
  }

  if (!form.okvedName.trim()) {
    errors.okvedName = required
  }

  for (const field of numberFields.value) {
    if (field.isRequired && form[field.key] === null) {
      errors[field.key] = required
    }
  }

  return errors
}

// Ошибки появляются после первой попытки отправки
const errors = computed<Partial<Record<FormErrorKey, string>>>(() => (isSubmitted.value ? getErrors() : {}))

const isFormValid = computed(() => Object.keys(getErrors()).length === 0)

function applyDefaults(loadedOptions: SandboxPersonaOptionsInterface) {
  const defaults = (paramId: string) =>
    loadedOptions.params.find((param) => param.id === paramId)?.defaultValue ?? null
  const textDefault = (paramId: string) => String(defaults(paramId) ?? '')
  const numberDefault = (paramId: string) => (typeof defaults(paramId) === 'number' ? Number(defaults(paramId)) : null)

  form.form = loadedOptions.forms.find((item) => item.id === String(defaults('form')))?.id ?? form.form
  form.okved = textDefault('okved')
  form.okvedName = textDefault('okved_name')

  for (const field of NUMBER_FIELDS) {
    form[field.key] = numberDefault(field.paramId)
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

    // При смене языка перезагружаются только подписи — введённое пользователем не сбрасываем
    if (isFirstLoad) {
      applyDefaults(options.value)
    }
  } catch (err: unknown) {
    console.error('Sandbox persona options loading failed:', err)
    optionsError.value = !options.value
  } finally {
    isOptionsLoading.value = false
  }
}

async function submitPersona() {
  if (isSubmitting.value || !options.value) return

  isSubmitted.value = true
  personaServerError.value = null

  if (!isFormValid.value) return

  isSubmitting.value = true

  try {
    const { data } = await sandboxService.createPersona($fetch, SandboxMapper.toPayload(form))

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.builder.createSuccess'),
      life: 4000,
    })

    await router.push({ name: 'sandbox', query: { persona: data.data.id } })
  } catch (err: unknown) {
    console.error('Sandbox persona creation failed:', err)

    const code = getApiErrorCode(err)

    if (code === ApiErrorCodeEnum.InnInvalid) {
      const suggestedInn = getApiProblem(err)?.suggested_inn

      innServerError.value = typeof suggestedInn === 'string'
        ? t('sandbox.builder.innChecksumHint', { inn: suggestedInn })
        : t('sandbox.builder.innChecksum')

      return
    }

    if (code === ApiErrorCodeEnum.InnTaken) {
      innServerError.value = t('sandbox.builder.innTaken')

      return
    }

    // «Такой компании не бывает» — бэкенд объясняет, какие параметры противоречат друг другу
    if (code === ApiErrorCodeEnum.PersonaInvalid) {
      personaServerError.value = getApiProblem(err)?.detail ?? t('toast.sandboxCreateError')

      return
    }

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.sandboxCreateError'),
      life: 4000,
    })
  } finally {
    isSubmitting.value = false
  }
}

function handleFlagsChange(flagIds: string[]) {
  form.flags = flagIds
}

function clearInnServerError() {
  innServerError.value = null
}

// ИНН задаёт форму: 12 цифр — ИП, 10 — организация
function syncFormWithInn(inn: string) {
  const trimmedInn = inn.trim()

  if (trimmedInn.length === IP_INN_LENGTH) {
    form.form = LegalFormEnum.SoleProprietor
  } else if (trimmedInn.length === LEGAL_INN_LENGTH && form.form === LegalFormEnum.SoleProprietor) {
    form.form = LegalFormEnum.Llc
  }
}

function dropInapplicableFlags() {
  const applicableIds = new Set(availableFlags.value.map((flag) => flag.id))

  form.flags = form.flags.filter((flagId) => applicableIds.has(flagId))
}

function handleInnChange(inn: string) {
  clearInnServerError()
  syncFormWithInn(inn)
}

function cancelBuilding() {
  router.push({ name: 'sandbox' })
}

watch(() => form.inn, handleInnChange)
watch(() => form.form, dropInapplicableFlags)
watch(locale, loadOptions)
onMounted(loadOptions)
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <SandboxDemoBadge />
      </template>
    </AppHeader>

    <main class="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <!-- Заголовок -->
      <div>
        <RouterLink
          :to="{ name: 'sandbox' }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary
                 transition-opacity hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('sandbox.builder.back') }}
        </RouterLink>

        <h1 class="mt-3 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('sandbox.builder.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm leading-relaxed text-fino-text-muted">
          {{ t('sandbox.builder.description') }}
        </p>
      </div>

      <SandboxPersonaBuilderPromo />

      <div class="grid grid-cols-1">
        <div
          class="min-w-0 rounded-3xl border border-fino-border bg-fino-surface
                 p-5 shadow-sm sm:p-8"
        >
          <SandboxPersonaBuilderSkeleton v-if="isOptionsLoading && !isOptionsReady" />

          <AppErrorState
            v-else-if="optionsError"
            :message="t('sandbox.builder.optionsLoadError')"
            is-inline
            @retry="loadOptions"
          />

          <form
            v-else-if="isOptionsReady"
            class="flex flex-col gap-8"
            novalidate
            :aria-busy="isSubmitting"
            @submit.prevent="submitPersona"
          >
            <!-- Пользователь и компания -->
            <section
              class="flex flex-col gap-4 border-b border-fino-border pb-8"
              :aria-label="t('sandbox.builder.sections.company')"
            >
              <h2 class="text-base font-bold text-fino-text">
                {{ t('sandbox.builder.sections.company') }}
              </h2>

              <div class="grid grid-cols-1 gap-4 lg:grid-cols-12">
                <SandboxPersonaField
                  class="lg:col-span-4"
                  input-id="persona-fullName"
                  :label="t('sandbox.builder.fields.fullName.label')"
                  :error="errors.fullName ?? null"
                >
                  <InputText
                    id="persona-fullName"
                    v-model="form.fullName"
                    :placeholder="t('sandbox.builder.fields.fullName.placeholder')"
                    :maxlength="FULL_NAME_MAX_LENGTH"
                    :invalid="Boolean(errors.fullName)"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  class="lg:col-span-5"
                  input-id="persona-organization"
                  :label="t('sandbox.builder.fields.organization.label')"
                  :hint="t('sandbox.builder.fields.organization.hint')"
                  :error="null"
                >
                  <InputText
                    id="persona-organization"
                    v-model="form.organization"
                    :placeholder="t('sandbox.builder.fields.organization.placeholder')"
                    :maxlength="ORGANIZATION_MAX_LENGTH"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  class="lg:col-span-3"
                  input-id="persona-inn"
                  :label="t('sandbox.builder.fields.inn.label')"
                  :hint="t('sandbox.builder.fields.inn.hint')"
                  :error="errors.inn ?? null"
                >
                  <InputText
                    id="persona-inn"
                    v-model="form.inn"
                    :placeholder="t('sandbox.builder.fields.inn.placeholder')"
                    maxlength="12"
                    inputmode="numeric"
                    :invalid="Boolean(errors.inn)"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  class="lg:col-span-4"
                  input-id="persona-form"
                  :label="t('sandbox.builder.fields.form.label')"
                  :error="null"
                >
                  <SelectButton
                    v-model="form.form"
                    :options="formOptions"
                    option-label="title"
                    option-value="id"
                    :allow-empty="false"
                    :disabled="isSubmitting"
                    :aria-label="t('sandbox.builder.fields.form.label')"
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  class="lg:col-span-3"
                  input-id="persona-okved"
                  :label="t('sandbox.builder.fields.okved.label')"
                  :error="errors.okved ?? null"
                >
                  <InputText
                    id="persona-okved"
                    v-model="form.okved"
                    :placeholder="t('sandbox.builder.fields.okved.placeholder')"
                    :maxlength="OKVED_MAX_LENGTH"
                    :invalid="Boolean(errors.okved)"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>

                <SandboxPersonaField
                  class="lg:col-span-5"
                  input-id="persona-okvedName"
                  :label="t('sandbox.builder.fields.okvedName.label')"
                  :error="errors.okvedName ?? null"
                >
                  <InputText
                    id="persona-okvedName"
                    v-model="form.okvedName"
                    :placeholder="t('sandbox.builder.fields.okvedName.placeholder')"
                    :maxlength="OKVED_NAME_MAX_LENGTH"
                    :invalid="Boolean(errors.okvedName)"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>
              </div>
            </section>

            <!-- Финансы и кредитная история: от них зависят остаток, прогноз и решение банка -->
            <section
              class="flex flex-col gap-4 border-b border-fino-border pb-8"
              :aria-label="t('sandbox.builder.sections.finance')"
            >
              <div>
                <h2 class="text-base font-bold text-fino-text">
                  {{ t('sandbox.builder.sections.finance') }}
                </h2>

                <p class="mt-1 text-sm text-fino-text-muted">
                  {{ t('sandbox.builder.sections.financeHint') }}
                </p>
              </div>

              <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
                <SandboxPersonaField
                  v-for="field in numberFields"
                  :key="field.key"
                  :input-id="`persona-${field.key}`"
                  :label="field.label"
                  :hint="field.hint"
                  :error="errors[field.key] ?? null"
                >
                  <InputNumber
                    v-model="form[field.key]"
                    :input-id="`persona-${field.key}`"
                    :min="field.min"
                    :max="field.max"
                    :min-fraction-digits="0"
                    :max-fraction-digits="field.fractionDigits"
                    :suffix="field.suffix"
                    :locale="locale"
                    :invalid="Boolean(errors[field.key])"
                    :disabled="isSubmitting"
                    fluid
                  />
                </SandboxPersonaField>
              </div>
            </section>

            <!-- Флаги: что с компанией «не так» -->
            <section
              v-if="availableFlags.length"
              class="flex flex-col gap-4"
              :aria-label="t('sandbox.builder.sections.flags')"
            >
              <div>
                <h2 class="text-base font-bold text-fino-text">
                  {{ t('sandbox.builder.sections.flags') }}
                </h2>

                <p class="mt-1 text-sm text-fino-text-muted">
                  {{ t('sandbox.builder.sections.flagsHint') }}
                </p>
              </div>

              <SandboxPersonaFlagsPicker
                :groups="options?.groups ?? []"
                :flags="availableFlags"
                :selected="form.flags"
                :is-disabled="isSubmitting"
                @change="handleFlagsChange"
              />
            </section>

            <Message
              v-if="personaServerError"
              severity="error"
              role="alert"
            >
              {{ personaServerError }}
            </Message>

            <!-- Действия -->
            <div class="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <Button
                type="button"
                severity="secondary"
                :label="t('sandbox.builder.cancel')"
                :disabled="isSubmitting"
                @click="cancelBuilding"
              />

              <Button
                type="submit"
                :label="t('sandbox.builder.submit')"
                icon="pi pi-check"
                :loading="isSubmitting"
              />
            </div>
          </form>
        </div>
      </div>
    </main>
  </div>
</template>
