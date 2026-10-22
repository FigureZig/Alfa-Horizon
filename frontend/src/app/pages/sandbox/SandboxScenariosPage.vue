<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import ApplicationStatusBadge from '@/app/features/application/components/ApplicationStatusBadge.vue'
import SandboxDemoBadge from '@/app/features/sandbox/components/SandboxDemoBadge.vue'
import SandboxGuideSkeleton from '@/app/features/sandbox/components/SandboxGuideSkeleton.vue'
import SandboxWorldPanel from '@/app/features/sandbox/components/SandboxWorldPanel.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxScenarioMapper } from '@/app/mappers/sandbox-scenario.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxEventCreateDto } from '@/app/types/sandbox/sandbox-world-dto'
import type {
  SandboxScenarioInterface,
  SandboxScenarioStepInterface,
} from '@/app/types/sandbox/sandbox-scenario-interface'

const ACTION_EVENT = 'event'
const HTTP_FORBIDDEN = 403

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

    // При смене языка сохраняем выбранный сценарий
    if (!selectedScenario.value) {
      selectedScenarioId.value = scenarios.value[0]?.id ?? null
    }
  } catch (err: unknown) {
    console.error('Sandbox scenarios loading failed:', err)
    hasError.value = true
  } finally {
    isLoading.value = false
  }
}

function selectScenario(scenario: SandboxScenarioInterface) {
  selectedScenarioId.value = scenario.id
}

function isForbiddenStep(step: SandboxScenarioStepInterface) {
  return step.expectedHttp === HTTP_FORBIDDEN
}

function isEventStep(step: SandboxScenarioStepInterface) {
  return step.action === ACTION_EVENT && Boolean(step.request.body)
}

async function loginAtStep(scenario: SandboxScenarioInterface, step: SandboxScenarioStepInterface) {
  if (!step.user || isBusy.value) return

  busyStepNumber.value = step.number

  try {
    const persona = await loginAsPersona(step.user.id)

    // Сотрудник банка работает в очереди, клиент — в заявках компании сценария
    if (persona.kind === SandboxPersonaKindEnum.Bank) {
      await router.push({ name: 'bank-queue', params: { inn: persona.inn } })
    } else {
      await router.push({ name: 'applications', params: { inn: scenario.company.inn } })
    }
  } catch (err: unknown) {
    console.error('Sandbox scenario login failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.loginError'),
      life: 4000,
    })
  } finally {
    busyStepNumber.value = null
  }
}

async function applyEventAtStep(step: SandboxScenarioStepInterface) {
  if (!step.request.body || isBusy.value) return

  busyStepNumber.value = step.number

  try {
    await sandboxService.createEvent($fetch, step.request.body as unknown as SandboxEventCreateDto)

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.scenarios.eventApplied'),
      life: 3000,
    })
  } catch (err: unknown) {
    console.error('Sandbox scenario event failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('sandbox.scenarios.eventError'),
      life: 4000,
    })
  } finally {
    busyStepNumber.value = null
  }
}

watch(locale, loadScenarios, { immediate: true })
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <div class="flex items-center gap-2">
          <SandboxWorldPanel />
          <SandboxDemoBadge />
        </div>
      </template>
    </AppHeader>

    <main class="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6 sm:px-6">
      <div>
        <RouterLink
          :to="{ name: 'sandbox' }"
          class="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:opacity-80"
        >
          <i
            class="pi pi-arrow-left text-xs"
            aria-hidden="true"
          />
          {{ t('sandbox.scenarios.back') }}
        </RouterLink>

        <p class="mt-4 text-xs font-bold uppercase tracking-widest text-primary">
          {{ t('sandbox.scenarios.eyebrow') }}
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('sandbox.scenarios.title') }}
        </h1>
        <p class="mt-2 max-w-2xl text-sm leading-relaxed text-fino-text-muted">
          {{ t('sandbox.scenarios.description') }}
        </p>
      </div>

      <SandboxGuideSkeleton v-if="isLoading && !scenarios.length" />

      <AppErrorState
        v-else-if="hasError"
        :message="t('sandbox.scenarios.loadError')"
        @retry="loadScenarios"
      />

      <p
        v-else-if="!scenarios.length"
        class="rounded-3xl border border-dashed border-fino-border bg-fino-surface px-6 py-12
               text-center text-sm text-fino-text-muted"
      >
        {{ t('sandbox.scenarios.empty') }}
      </p>

      <div
        v-else
        class="grid items-start gap-6 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)]"
      >
        <!-- Список сценариев -->
        <nav
          class="grid gap-3 sm:grid-cols-2 lg:grid-cols-1"
          :aria-label="t('sandbox.scenarios.listLabel')"
        >
          <button
            v-for="scenario in scenarios"
            :key="scenario.id"
            type="button"
            class="cursor-pointer rounded-2xl border bg-fino-surface p-4 text-left transition-colors
                   hover:border-primary focus-visible:outline-2 focus-visible:outline-primary
                   motion-reduce:transition-none"
            :class="scenario.id === selectedScenarioId ? 'border-primary bg-fino-accent' : 'border-fino-border'"
            :aria-current="scenario.id === selectedScenarioId"
            @click="selectScenario(scenario)"
          >
            <span class="block break-words text-sm font-bold text-fino-text">{{ scenario.title }}</span>
            <span class="mt-1 block break-words text-xs text-fino-text-muted">{{ scenario.company.name }}</span>
          </button>
        </nav>

        <!-- Шаги выбранного сценария -->
        <section
          v-if="selectedScenario"
          class="min-w-0 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6"
        >
          <h2 class="break-words text-xl font-bold text-fino-text">
            {{ selectedScenario.title }}
          </h2>

          <p class="mt-2 text-sm leading-relaxed text-fino-text-muted">
            {{ selectedScenario.about }}
          </p>

          <p class="mt-3 break-words text-xs font-semibold text-fino-text-muted">
            {{ t('sandbox.scenarios.company', { name: selectedScenario.company.name }) }}
            · {{ selectedScenario.company.inn }}
          </p>

          <ol class="mt-6 flex flex-col gap-4">
            <li
              v-for="step in selectedScenario.steps"
              :key="step.number"
              class="flex gap-3 rounded-2xl border border-fino-border bg-fino-surface-secondary p-4"
            >
              <span
                class="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary
                       text-sm font-bold text-primary-contrast"
              >
                {{ step.number }}
              </span>

              <div class="flex min-w-0 flex-1 flex-col gap-2">
                <p class="break-words text-sm text-fino-text">
                  <span class="font-bold">{{ step.user ? step.user.fullName : t('sandbox.scenarios.system') }}</span>
                  {{ step.title }}
                </p>

                <p
                  v-if="step.note"
                  class="break-words text-sm leading-relaxed text-fino-text-muted"
                >
                  {{ step.note }}
                </p>

                <div class="flex flex-wrap items-center gap-2">
                  <span
                    v-if="isForbiddenStep(step)"
                    class="rounded-lg bg-red-500/10 px-2.5 py-1 text-xs font-semibold
                           text-red-700 dark:text-red-400"
                  >
                    {{ t('sandbox.scenarios.expectedForbidden') }}
                  </span>

                  <template v-else-if="step.expectedStatus">
                    <span class="text-xs text-fino-text-muted">{{ t('sandbox.scenarios.expectedStatus') }}</span>
                    <ApplicationStatusBadge :status="step.expectedStatus" />
                  </template>
                </div>

                <code class="block break-all text-xs text-fino-text-muted">
                  {{ step.request.method }} {{ step.request.path }}
                </code>

                <div>
                  <button
                    v-if="step.user"
                    type="button"
                    class="cursor-pointer rounded-xl bg-primary px-4 py-2 text-sm font-semibold
                           text-primary-contrast transition-opacity hover:opacity-90
                           disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
                    :disabled="isBusy"
                    @click="loginAtStep(selectedScenario, step)"
                  >
                    {{ t('sandbox.scenarios.loginAs', { name: step.user.fullName }) }}
                  </button>

                  <button
                    v-else-if="isEventStep(step)"
                    type="button"
                    class="cursor-pointer rounded-xl border border-fino-border px-4 py-2 text-sm font-semibold
                           text-fino-text transition-colors hover:bg-fino-surface-hover
                           disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
                    :disabled="isBusy"
                    @click="applyEventAtStep(step)"
                  >
                    {{ t('sandbox.scenarios.applyEvent') }}
                  </button>
                </div>
              </div>
            </li>
          </ol>
        </section>
      </div>
    </main>
  </div>
</template>
