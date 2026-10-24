<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import Skeleton from 'primevue/skeleton'
import AppErrorState from '@/app/components/AppErrorState.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { EVENT_ACTION, FORBIDDEN_ACTION, useScenarioRun } from '@/app/composables/useScenarioRun'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxScenarioMapper } from '@/app/mappers/sandbox-scenario.mapper'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type {
  SandboxScenarioInterface,
  SandboxScenarioStepInterface,
} from '@/app/types/sandbox/sandbox-scenario-interface'

interface ScenarioPersonInterface {
  id: string
  fullName: string
  initials: string
}

const ACTION_VOTE = 'vote'
const SKELETON_CARDS = 4
// Нормы закона в описании сценария — в скобках; на карточке их не показываем
const LAW_REFERENCE_PATTERN = /\s*\([^()]*(?:ст\.|ФЗ|ГК|art\.|Art\.)[^()]*\)/g

// Ожидаемый статус — цветом, как его увидит пользователь на странице заявки
const STATUS_TONES: Partial<Record<ApplicationDetailStatusEnum, string>> = {
  [ApplicationDetailStatusEnum.Issued]: 'bg-fino-lime text-[#111]',
  [ApplicationDetailStatusEnum.Signed]: 'bg-fino-lime text-[#111]',
  [ApplicationDetailStatusEnum.Rejected]: 'bg-primary text-primary-contrast',
  [ApplicationDetailStatusEnum.Withdrawn]: 'bg-primary text-primary-contrast',
  [ApplicationDetailStatusEnum.Offered]: 'bg-fino-amber text-[#111]',
  [ApplicationDetailStatusEnum.Signing]: 'bg-fino-amber text-[#111]',
  [ApplicationDetailStatusEnum.InfoRequested]: 'bg-fino-amber text-[#111]',
}
const NEUTRAL_TONE = 'bg-fino-surface-secondary text-fino-text'

const emit = defineEmits<{
  navigated: []
}>()

const { t, locale } = useI18n({ useScope: 'global' })
const toast = useToast()
const $fetch = useApiFetch()
// Открытый сценарий общий с панелью: экран входа открывает её сразу на нужном
const { openScenarioId } = useReviewerPanel()
const run = useScenarioRun()

const scenarios = ref<SandboxScenarioInterface[]>([])
const isLoading = ref(false)
const hasError = ref(false)
const isResetting = ref(false)
const scenarioToRestart = ref<Nullable<SandboxScenarioInterface>>(null)
const isRestartConfirmVisible = ref(false)

const isBusy = computed(() => run.isBusy.value || isResetting.value)

const cards = computed(() =>
  scenarios.value.map((scenario) => ({
    scenario,
    about: scenario.about.replace(LAW_REFERENCE_PATTERN, ''),
    people: getPeople(scenario),
    isVoting: scenario.steps.some((step) => step.action === ACTION_VOTE),
    isActive: run.scenario.value?.id === scenario.id,
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

function isActiveStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  return run.scenario.value?.id === scenario.id && run.isStepCurrent(step)
}

function isDoneStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  return run.scenario.value?.id === scenario.id && run.isStepDone(step)
}

function getStepClass(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (isActiveStep(scenario, step)) return 'border-fino-line bg-fino-lime-soft shadow-[3px_3px_0_var(--fino-shadow)]'
  if (isDoneStep(scenario, step)) return 'border-fino-border opacity-70'

  return 'border-fino-border'
}

function isEventStep(step: SandboxScenarioStepInterface) {
  return step.action === EVENT_ACTION && Boolean(step.request.body)
}

function isForbiddenStep(step: SandboxScenarioStepInterface) {
  return step.action === FORBIDDEN_ACTION
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

// Войти человеком шага: сценарий запоминает, на каком шаге мы, и дальше идёт сам
async function loginAtStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (!step.user || isBusy.value) return

  run.start(scenario, step.number)

  try {
    await run.goToStep(step)

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.scenarios.loggedInAs', { name: step.user.fullName }),
      life: 3000,
    })

    emit('navigated')
  } catch (err: unknown) {
    console.error('Reviewer scenario login failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('toast.loginError'), life: 4000 })
  }
}

async function applyEventAtStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (isBusy.value) return

  if (run.scenario.value?.id !== scenario.id) run.start(scenario, step.number)

  try {
    await run.applyEvent(step)

    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.eventApplied'), life: 4000 })
  } catch (err: unknown) {
    console.error('Reviewer scenario event failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.scenarios.eventError'), life: 4000 })
  }
}

// Начать (или продолжить) сценарий: сразу входим человеком текущего шага
function continueScenario(scenario: SandboxScenarioInterface) {
  const isActive = run.scenario.value?.id === scenario.id
  const step = isActive && run.currentStep.value ? run.currentStep.value : scenario.steps[0]

  if (!step) return

  if (step.user) {
    loginAtStep(scenario, step)
  } else if (!isActive) {
    run.start(scenario, step.number)
  }
}

function askRestart(scenario: SandboxScenarioInterface) {
  scenarioToRestart.value = scenario
  isRestartConfirmVisible.value = true
}

function cancelRestart() {
  isRestartConfirmVisible.value = false
}

// Пройти заново: мир — как в начале (без событий, отказов и перемотки времени), сценарий — с шага 1
async function confirmRestart() {
  const scenario = scenarioToRestart.value

  isRestartConfirmVisible.value = false

  if (!scenario || isBusy.value) return

  isResetting.value = true

  try {
    await sandboxService.reset($fetch)
    run.start(scenario, 1)

    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.restart.done'), life: 4000 })
  } catch (err: unknown) {
    console.error('Reviewer world reset failed:', err)

    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.world.commandError'), life: 4000 })

    return
  } finally {
    isResetting.value = false
  }

  continueScenario(scenario)
}

function getScenarioElementId(scenarioId: string) {
  return `reviewer-scenario-${scenarioId}`
}

// Сценарий, открытый снаружи, — прокручиваем к нему, когда список уже на экране
async function scrollToOpenScenario() {
  if (!openScenarioId.value || !scenarios.value.length) return

  await nextTick()
  document.getElementById(getScenarioElementId(openScenarioId.value))?.scrollIntoView({ block: 'start' })
}

onMounted(loadScenarios)
watch([openScenarioId, scenarios], scrollToOpenScenario)
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
        :id="getScenarioElementId(card.scenario.id)"
        :key="card.scenario.id"
        class="rounded-2xl border-2 bg-fino-surface transition-colors motion-reduce:transition-none"
        :class="openScenarioId === card.scenario.id ? 'border-fino-line' : 'border-fino-border'"
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
            <span class="flex flex-wrap items-center gap-2">
              <span class="break-words font-display text-base font-extrabold text-fino-text">{{ card.scenario.title }}</span>
              <span
                v-if="card.isActive"
                class="rounded-md border-2 border-fino-line bg-fino-lime px-1.5 font-mono text-[10px] font-bold uppercase
                       text-[#111]"
              >
                {{ run.isFinished.value ? t('sandbox.scenarios.badgeDone') : t('sandbox.scenarios.badgeActive') }}
              </span>
            </span>
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
                class="-ml-1.5 flex size-7 items-center justify-center rounded-full border-2 border-fino-line
                       bg-fino-lime text-[10px] font-bold text-[#111] first:ml-0"
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
          <!-- Главное действие: начать или продолжить с текущего шага; «заново» — со сбросом мира -->
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold
                     text-primary-contrast btn-key disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isBusy || (card.isActive && run.isFinished.value)"
              @click="continueScenario(card.scenario)"
            >
              {{ card.isActive && run.currentStep.value
                ? t('sandbox.scenarios.continue', { number: run.currentStep.value.number })
                : t('sandbox.scenarios.start') }}
              <i
                class="pi pi-arrow-right text-xs"
                aria-hidden="true"
              />
            </button>

            <button
              type="button"
              class="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl bg-fino-surface px-3.5 text-sm
                     font-semibold text-fino-text btn-key disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="isBusy"
              @click="askRestart(card.scenario)"
            >
              <i
                :class="isResetting ? 'pi pi-spinner pi-spin' : 'pi pi-refresh'"
                class="text-xs"
                aria-hidden="true"
              />
              {{ t('sandbox.scenarios.restart.button') }}
            </button>
          </div>

          <p class="text-xs leading-relaxed text-fino-text-muted">
            {{ t('sandbox.scenarios.restart.hint') }}
          </p>

          <p class="break-words text-xs font-semibold text-fino-text-muted">
            {{ t('sandbox.scenarios.company', { name: card.scenario.company.name }) }}
          </p>

          <ol class="flex flex-col gap-2">
            <li
              v-for="step in card.scenario.steps"
              :key="step.number"
              class="flex gap-3 rounded-xl border-2 p-3 transition-colors motion-reduce:transition-none"
              :class="getStepClass(card.scenario, step)"
              :aria-current="isActiveStep(card.scenario, step) ? 'step' : undefined"
            >
              <span
                class="flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-fino-line text-[11px]
                       font-bold"
                :class="isDoneStep(card.scenario, step) ? 'bg-primary text-primary-contrast' : 'bg-fino-surface text-fino-text'"
              >
                <i
                  v-if="isDoneStep(card.scenario, step)"
                  class="pi pi-check text-[10px] motion-safe:animate-tick-pop"
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
                    class="rounded-lg border-2 border-fino-line bg-primary px-2 py-0.5 text-xs font-semibold
                           text-primary-contrast"
                  >
                    {{ t('sandbox.scenarios.expectedForbidden') }}
                  </span>

                  <template v-else-if="step.expectedStatus">
                    <span class="text-xs text-fino-text-muted">{{ t('sandbox.scenarios.expectedStatus') }}</span>
                    <span
                      class="rounded-lg border-2 border-fino-line px-2 py-0.5 text-xs font-semibold"
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
                    class="cursor-pointer rounded-xl px-3.5 py-2 text-xs font-semibold btn-key disabled:cursor-not-allowed
                           disabled:opacity-50"
                    :class="isActiveStep(card.scenario, step) ? 'bg-primary text-primary-contrast' : 'bg-fino-surface text-fino-text'"
                    :disabled="isBusy"
                    @click="loginAtStep(card.scenario, step)"
                  >
                    {{ t('sandbox.scenarios.loginAs', { name: step.user.fullName }) }}
                  </button>

                  <button
                    v-else
                    type="button"
                    class="cursor-pointer rounded-xl bg-fino-surface px-3.5 py-2 text-xs font-semibold text-fino-text btn-key
                           disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="isBusy"
                    @click="applyEventAtStep(card.scenario, step)"
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
      v-model:visible="isRestartConfirmVisible"
      modal
      :header="t('sandbox.scenarios.restart.title')"
      :style="{ width: '28rem', maxWidth: '92vw' }"
    >
      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ t('sandbox.scenarios.restart.text') }}
      </p>

      <template #footer>
        <button
          type="button"
          class="cursor-pointer rounded-xl px-4 py-2 text-sm font-semibold text-fino-text transition-colors
                 hover:bg-fino-surface-hover motion-reduce:transition-none"
          @click="cancelRestart"
        >
          {{ t('sandbox.scenarios.restart.cancel') }}
        </button>

        <button
          type="button"
          class="cursor-pointer rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-contrast btn-key"
          @click="confirmRestart"
        >
          {{ t('sandbox.scenarios.restart.confirm') }}
        </button>
      </template>
    </Dialog>
  </div>
</template>
