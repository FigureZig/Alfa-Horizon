<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationStatusBadge from '@/app/features/application/components/ApplicationStatusBadge.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxScenarioMapper } from '@/app/mappers/sandbox-scenario.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { AppLocale } from '@/app/i18n'
import type { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxEventCreateDto } from '@/app/types/sandbox/sandbox-world-dto'
import type {
  SandboxScenarioInterface,
  SandboxScenarioStepInterface,
} from '@/app/types/sandbox/sandbox-scenario-interface'

const ACTION_EVENT = 'event'
const HTTP_FORBIDDEN = 403
const SKELETON_STEPS = 3

const props = defineProps<{
  // Заявка на текущем экране: по её статусу отмечаем шаги, которые уже совпали
  applicationId: Nullable<string>
  applicationStatus: Nullable<ApplicationDetailStatusEnum>
}>()

const emit = defineEmits<{
  navigated: []
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()
const { loginAsPersona } = useSession()

const scenarios = ref<SandboxScenarioInterface[]>([])
const selectedScenarioId = ref<Nullable<string>>(null)
const isLoading = ref(false)
const hasError = ref(false)
// Шаг, который сейчас выполняется: вход персоной или событие мира
const busyStepNumber = ref<Nullable<number>>(null)

const selectedScenario = computed(() =>
  scenarios.value.find((scenario) => scenario.id === selectedScenarioId.value) ?? null,
)
const isBusy = computed(() => busyStepNumber.value !== null)

async function loadScenarios() {
  if (isLoading.value) return

  isLoading.value = true
  hasError.value = false

  try {
    const { data } = await sandboxService.fetchScenarios($fetch, locale.value as AppLocale)

    scenarios.value = data.data.map((scenario) => SandboxScenarioMapper.toEntity(scenario))
    selectedScenarioId.value = scenarios.value[0]?.id ?? null
  } catch (err: unknown) {
    console.error('Sandbox scenarios loading failed:', err)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

function isForbiddenStep(step: SandboxScenarioStepInterface) {
  return step.expectedHttp === HTTP_FORBIDDEN
}

function isEventStep(step: SandboxScenarioStepInterface) {
  return step.action === ACTION_EVENT && Boolean(step.request.body)
}

// Статус заявки на экране совпал с ожидаемым после шага: ставим галочку
function isStatusMatched(step: SandboxScenarioStepInterface) {
  return Boolean(props.applicationStatus && step.expectedStatus === props.applicationStatus)
}

async function loginAtStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (!step.user || isBusy.value) return

  busyStepNumber.value = step.number

  try {
    const persona = await loginAsPersona(step.user.id)

    // Сотрудник банка — в очередь; клиент — к той же заявке, если она открыта, иначе к заявкам компании сценария
    if (persona.kind === SandboxPersonaKindEnum.Bank) {
      await router.push({ name: 'bank-queue', params: { inn: persona.inn } })
    } else if (props.applicationId) {
      await router.push({ name: 'application', params: { inn: scenario.company.inn, applicationId: props.applicationId } })
    } else {
      await router.push({ name: 'applications', params: { inn: scenario.company.inn } })
    }

    emit('navigated')
  } catch (err: unknown) {
    console.error('Reviewer scenario login failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('toast.loginError'), life: 4000 })
  } finally {
    busyStepNumber.value = null
  }
}

async function applyEventAtStep(step: SandboxScenarioStepInterface) {
  if (!step.request.body || isBusy.value) return

  busyStepNumber.value = step.number

  try {
    await sandboxService.createEvent($fetch, step.request.body as unknown as SandboxEventCreateDto)

    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.eventApplied'), life: 3000 })
  } catch (err: unknown) {
    console.error('Reviewer scenario event failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.scenarios.eventError'), life: 4000 })
  } finally {
    busyStepNumber.value = null
  }
}

onMounted(loadScenarios)
</script>

<template>
  <div class="flex flex-col gap-4">
    <div
      v-if="isLoading && !scenarios.length"
      class="flex flex-col gap-3"
      aria-busy="true"
    >
      <Skeleton
        height="2.75rem"
        border-radius="0.75rem"
      />
      <Skeleton
        v-for="index in SKELETON_STEPS"
        :key="index"
        height="6rem"
        border-radius="1rem"
      />
    </div>

    <AppErrorState
      v-else-if="hasError"
      :message="t('sandbox.scenarios.loadError')"
      is-inline
      @retry="loadScenarios"
    />

    <p
      v-else-if="!scenarios.length"
      class="text-sm text-fino-text-muted"
    >
      {{ t('sandbox.scenarios.empty') }}
    </p>

    <template v-else>
      <Select
        v-model="selectedScenarioId"
        :options="scenarios"
        option-label="title"
        option-value="id"
        :aria-label="t('reviewer.scenarios.pick')"
        fluid
      />

      <template v-if="selectedScenario">
        <p class="text-sm leading-relaxed text-fino-text-muted">
          {{ selectedScenario.about }}
        </p>

        <p class="break-words text-xs font-semibold text-fino-text-muted">
          {{ t('sandbox.scenarios.company', { name: selectedScenario.company.name }) }}
        </p>

        <ol class="flex flex-col gap-3">
          <li
            v-for="step in selectedScenario.steps"
            :key="step.number"
            class="flex gap-3 rounded-2xl border bg-fino-surface p-3"
            :class="isStatusMatched(step) ? 'border-green-500/40' : 'border-fino-border'"
          >
            <span
              class="flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold"
              :class="isStatusMatched(step) ? 'bg-green-500 text-white' : 'bg-primary text-primary-contrast'"
            >
              <i
                v-if="isStatusMatched(step)"
                class="pi pi-check text-xs"
                aria-hidden="true"
              />
              <template v-else>
                {{ step.number }}
              </template>
            </span>

            <div class="flex min-w-0 flex-1 flex-col gap-2">
              <p class="break-words text-sm text-fino-text">
                <span class="font-bold">{{ step.user ? step.user.fullName : t('sandbox.scenarios.system') }}</span>
                {{ step.title }}
              </p>

              <p
                v-if="step.note"
                class="break-words text-xs leading-relaxed text-fino-text-muted"
              >
                {{ step.note }}
              </p>

              <div class="flex flex-wrap items-center gap-2">
                <span
                  v-if="isForbiddenStep(step)"
                  class="rounded-lg bg-red-500/10 px-2 py-0.5 text-xs font-semibold text-red-700 dark:text-red-400"
                >
                  {{ t('sandbox.scenarios.expectedForbidden') }}
                </span>

                <template v-else-if="step.expectedStatus">
                  <span class="text-xs text-fino-text-muted">{{ t('sandbox.scenarios.expectedStatus') }}</span>
                  <ApplicationStatusBadge :status="step.expectedStatus" />
                </template>
              </div>

              <div>
                <button
                  v-if="step.user"
                  type="button"
                  class="cursor-pointer rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast
                         transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50
                         motion-reduce:transition-none"
                  :disabled="isBusy"
                  @click="loginAtStep(selectedScenario, step)"
                >
                  {{ t('sandbox.scenarios.loginAs', { name: step.user.fullName }) }}
                </button>

                <button
                  v-else-if="isEventStep(step)"
                  type="button"
                  class="cursor-pointer rounded-xl border border-fino-border px-3.5 py-2 text-xs font-semibold text-fino-text
                         transition-colors hover:bg-fino-surface-hover disabled:cursor-not-allowed disabled:opacity-50
                         motion-reduce:transition-none"
                  :disabled="isBusy"
                  @click="applyEventAtStep(step)"
                >
                  {{ t('sandbox.scenarios.applyEvent') }}
                </button>
              </div>
            </div>
          </li>
        </ol>
      </template>
    </template>
  </div>
</template>
