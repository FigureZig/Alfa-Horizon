<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Skeleton from 'primevue/skeleton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxScenarioMapper } from '@/app/mappers/sandbox-scenario.mapper'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { AppLocale } from '@/app/i18n'
import type { CompanyAccessInterface } from '@/app/types/company/company-access-interface'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxEventCreateDto } from '@/app/types/sandbox/sandbox-world-dto'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type {
  SandboxScenarioInterface,
  SandboxScenarioStepInterface,
} from '@/app/types/sandbox/sandbox-scenario-interface'

interface ScenarioPersonInterface {
  id: string
  fullName: string
  initials: string
}

const ACTION_EVENT = 'event'
const ACTION_VOTE = 'vote'
const HTTP_FORBIDDEN = 403
const SKELETON_CARDS = 4
// Нормы закона в описании сценария — в скобках; на карточке их не показываем
const LAW_REFERENCE_PATTERN = /\s*\([^()]*(?:ст\.|ФЗ|ГК|art\.|Art\.)[^()]*\)/g

// Ожидаемый статус теми же словами, что увидит пользователь на странице заявки
const STATUS_TONES: Partial<Record<ApplicationDetailStatusEnum, string>> = {
  [ApplicationDetailStatusEnum.Issued]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [ApplicationDetailStatusEnum.Signed]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [ApplicationDetailStatusEnum.Rejected]: 'bg-red-500/10 text-red-700 dark:text-red-400',
  [ApplicationDetailStatusEnum.Withdrawn]: 'bg-red-500/10 text-red-700 dark:text-red-400',
  [ApplicationDetailStatusEnum.Offered]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  [ApplicationDetailStatusEnum.Signing]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  [ApplicationDetailStatusEnum.InfoRequested]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
}
const NEUTRAL_TONE = 'bg-fino-surface-secondary text-fino-text-muted'

const props = defineProps<{
  // Заявка на текущем экране: по её статусу отмечаем шаги, которые уже совпали
  applicationId: Nullable<string>
  // Компания открытой заявки: к заявке ведём, только если она из этого сценария
  applicationInn: Nullable<string>
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
const openScenarioId = ref<Nullable<string>>(null)
const isLoading = ref(false)
const hasError = ref(false)
// Шаг, который сейчас выполняется: вход, событие мира или сброс (0)
const busyStepNumber = ref<Nullable<number>>(null)
const isResetConfirmVisible = ref(false)

const isBusy = computed(() => busyStepNumber.value !== null)

const cards = computed(() =>
  scenarios.value.map((scenario) => ({
    scenario,
    about: scenario.about.replace(LAW_REFERENCE_PATTERN, ''),
    people: getPeople(scenario),
    isVoting: scenario.steps.some((step) => step.action === ACTION_VOTE),
  })),
)

// Кто по очереди: люди сценария в порядке первого шага
function getPeople(scenario: SandboxScenarioInterface): ScenarioPersonInterface[] {
  const people = new Map<string, ScenarioPersonInterface>()

  for (const step of scenario.steps) {
    if (step.user && !people.has(step.user.id)) {
      const initials = step.user.fullName.split(/\s+/).map((part) => part[0]).join('').slice(0, 2)

      people.set(step.user.id, { id: step.user.id, fullName: step.user.fullName, initials })
    }
  }

  return [...people.values()]
}

async function loadScenarios() {
  if (isLoading.value) return

  isLoading.value = true
  hasError.value = false

  try {
    const { data } = await sandboxService.fetchScenarios($fetch, locale.value as AppLocale)

    scenarios.value = data.data.map((scenario) => SandboxScenarioMapper.toEntity(scenario))
  } catch (err: unknown) {
    console.error('Sandbox scenarios loading failed:', err)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

function toggleScenario(scenarioId: string) {
  openScenarioId.value = openScenarioId.value === scenarioId ? null : scenarioId
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

// Голосование и дозапрос — один статус, но человек видит разное: «Ждём решения участников» или «Банк просит данные»
function getExpectedLabel(step: SandboxScenarioStepInterface, isVoting: boolean): string {
  if (!step.expectedStatus) return ''

  if (step.expectedStatus === ApplicationDetailStatusEnum.InfoRequested) {
    return isVoting ? t('sandbox.scenarios.expected.voting') : t('sandbox.scenarios.expected.info')
  }

  return t(`application.status.${step.expectedStatus}`)
}

function getExpectedTone(step: SandboxScenarioStepInterface): string {
  return (step.expectedStatus && STATUS_TONES[step.expectedStatus]) || NEUTRAL_TONE
}

function askReset() {
  isResetConfirmVisible.value = true
}

function cancelReset() {
  isResetConfirmVisible.value = false
}

// Сценарии мешают друг другу: события реестров и отказы живут до сброса мира
async function confirmReset() {
  isResetConfirmVisible.value = false

  if (isBusy.value) return

  busyStepNumber.value = 0

  try {
    await sandboxService.reset($fetch)

    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.resetDone'), life: 3000 })
  } catch (err: unknown) {
    console.error('Reviewer world reset failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.world.commandError'), life: 4000 })
  } finally {
    busyStepNumber.value = null
  }
}

// Куда вести после входа: к открытой заявке сценария — в том виде, в каком её видит этот человек
function getStepRoute(
  scenario: SandboxScenarioInterface,
  persona: SandboxPersonaInterface,
  companies: CompanyAccessInterface[],
): RouteLocationRaw {
  const companyInn = scenario.company.inn
  const applicationId = props.applicationInn === companyInn ? props.applicationId : null

  // Сотрудник банка — в досье этой заявки, без неё — в очередь
  if (persona.kind === SandboxPersonaKindEnum.Bank) {
    return applicationId
      ? { name: 'bank-dossier', params: { inn: persona.inn, applicationId } }
      : { name: 'bank-queue', params: { inn: persona.inn } }
  }

  const access = companies.find((company) => company.inn === companyInn)

  // Участник без доступа к счёту видит только голосование
  if (access && !access.canView && access.canApprove) {
    return applicationId
      ? { name: 'vote', params: { inn: companyInn, applicationId } }
      : { name: 'votes', params: { inn: companyInn } }
  }

  return applicationId
    ? { name: 'application', params: { inn: companyInn, applicationId } }
    : { name: 'applications', params: { inn: companyInn } }
}

async function loginAtStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (!step.user || isBusy.value) return

  busyStepNumber.value = step.number

  try {
    const { persona, companies } = await loginAsPersona(step.user.id)

    // Тот же адрес другим человеком — кабинет сам перечитает шапку, права и страницу
    await router.push(getStepRoute(scenario, persona, companies))

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.scenarios.loggedInAs', { name: persona.fullName }),
      life: 3000,
    })

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

    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.eventApplied'), life: 4000 })
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
  <div class="flex flex-col gap-3">
    <div
      v-if="isLoading && !scenarios.length"
      class="flex flex-col gap-3"
      aria-busy="true"
    >
      <Skeleton
        v-for="index in SKELETON_CARDS"
        :key="index"
        height="5.5rem"
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

    <ul
      v-else
      class="flex flex-col gap-3"
    >
      <li
        v-for="card in cards"
        :key="card.scenario.id"
        class="rounded-2xl border bg-fino-surface transition-colors motion-reduce:transition-none"
        :class="openScenarioId === card.scenario.id ? 'border-primary/40' : 'border-fino-border'"
      >
        <!-- Карточка сценария: название, о чём и кто по очереди -->
        <button
          type="button"
          class="flex w-full cursor-pointer items-start gap-3 rounded-2xl p-4 text-left
                 focus-visible:outline-2 focus-visible:outline-primary"
          :aria-expanded="openScenarioId === card.scenario.id"
          @click="toggleScenario(card.scenario.id)"
        >
          <span class="min-w-0 flex-1">
            <span class="block break-words text-sm font-bold text-fino-text">{{ card.scenario.title }}</span>
            <span
              class="mt-1 block break-words text-xs leading-relaxed text-fino-text-muted"
              :class="{ 'line-clamp-2': openScenarioId !== card.scenario.id }"
            >{{ card.about }}</span>

            <span
              class="mt-2 flex items-center"
              :aria-label="t('sandbox.scenarios.roles')"
            >
              <span
                v-for="person in card.people"
                :key="person.id"
                class="-ml-1.5 flex size-7 items-center justify-center rounded-full border-2 border-fino-surface
                       bg-fino-accent text-[10px] font-bold text-primary first:ml-0"
                :title="person.fullName"
              >
                {{ person.initials }}
              </span>
            </span>
          </span>

          <i
            class="pi pi-chevron-down mt-1 text-xs text-fino-text-muted transition-transform duration-200
                   motion-reduce:transition-none"
            :class="{ 'rotate-180': openScenarioId === card.scenario.id }"
            aria-hidden="true"
          />
        </button>

        <div
          v-if="openScenarioId === card.scenario.id"
          class="flex flex-col gap-3 px-4 pb-4"
        >
          <!-- Сценарии мешают друг другу: начинать лучше с чистого мира -->
          <button
            type="button"
            class="inline-flex min-h-10 w-fit cursor-pointer items-center gap-2 rounded-xl border border-fino-border
                   px-3.5 text-xs font-semibold text-fino-text transition-colors hover:bg-fino-surface-hover
                   disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
            :disabled="isBusy"
            @click="askReset"
          >
            <i
              :class="busyStepNumber === 0 ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'"
              class="text-xs"
              aria-hidden="true"
            />
            {{ t('sandbox.scenarios.reset') }}
          </button>

          <p class="break-words text-xs font-semibold text-fino-text-muted">
            {{ t('sandbox.scenarios.company', { name: card.scenario.company.name }) }}
          </p>

          <ol class="flex flex-col gap-2">
            <li
              v-for="step in card.scenario.steps"
              :key="step.number"
              class="flex gap-3 rounded-xl border p-3"
              :class="isStatusMatched(step) ? 'border-green-500/40' : 'border-fino-border'"
            >
              <span
                class="flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] font-bold"
                :class="isStatusMatched(step) ? 'bg-green-500 text-white' : 'bg-fino-surface-secondary text-fino-text'"
              >
                <i
                  v-if="isStatusMatched(step)"
                  class="pi pi-check text-[10px]"
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
                    <span
                      class="rounded-lg px-2 py-0.5 text-xs font-semibold"
                      :class="getExpectedTone(step)"
                    >
                      {{ getExpectedLabel(step, card.isVoting) }}
                    </span>
                  </template>
                </div>

                <div v-if="step.user || isEventStep(step)">
                  <button
                    v-if="step.user"
                    type="button"
                    class="cursor-pointer rounded-xl bg-primary px-3.5 py-2 text-xs font-semibold text-primary-contrast
                           transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50
                           motion-reduce:transition-none"
                    :disabled="isBusy"
                    @click="loginAtStep(card.scenario, step)"
                  >
                    {{ t('sandbox.scenarios.loginAs', { name: step.user.fullName }) }}
                  </button>

                  <button
                    v-else
                    type="button"
                    class="cursor-pointer rounded-xl border border-fino-border px-3.5 py-2 text-xs font-semibold
                           text-fino-text transition-colors hover:bg-fino-surface-hover disabled:cursor-not-allowed
                           disabled:opacity-50 motion-reduce:transition-none"
                    :disabled="isBusy"
                    @click="applyEventAtStep(step)"
                  >
                    {{ t('sandbox.scenarios.applyEvent') }}
                  </button>
                </div>
              </div>
            </li>
          </ol>
        </div>
      </li>
    </ul>

    <Dialog
      v-model:visible="isResetConfirmVisible"
      modal
      :header="t('sandbox.world.reset.confirmTitle')"
      :style="{ width: '26rem', maxWidth: '92vw' }"
    >
      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ t('sandbox.world.reset.confirmText') }}
      </p>

      <template #footer>
        <button
          type="button"
          class="cursor-pointer rounded-xl border border-fino-border px-4 py-2 text-sm font-semibold
                 text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
          @click="cancelReset"
        >
          {{ t('sandbox.world.reset.cancel') }}
        </button>

        <button
          type="button"
          class="cursor-pointer rounded-xl bg-primary px-4 py-2 text-sm font-semibold
                 text-primary-contrast transition-opacity hover:opacity-90 motion-reduce:transition-none"
          @click="confirmReset"
        >
          {{ t('sandbox.world.reset.confirm') }}
        </button>
      </template>
    </Dialog>
  </div>
</template>
