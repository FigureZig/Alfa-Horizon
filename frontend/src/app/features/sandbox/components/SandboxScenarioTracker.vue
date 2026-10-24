<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'
import { EVENT_ACTION, FORBIDDEN_ACTION, SYSTEM_ACTION, useScenarioRun } from '@/app/composables/useScenarioRun'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationMapper } from '@/app/mappers/application.mapper'

// Пока банк работает сам, статус заявки сценария проверяем раз в несколько секунд
const POLL_MS = 3000

const { t } = useI18n({ useScope: 'global' })
const toast = useToast()
const $fetch = useApiFetch()
const { demoPersona } = useDemoPersona()
const { openPanel } = useReviewerPanel()
const run = useScenarioRun()

const step = computed(() => run.currentStep.value)
// Свёрнутая плашка — прогресс и главная кнопка без пояснений; на телефоне свёрнута сразу, чтобы не закрывать страницу
const isCollapsed = ref(window.matchMedia('(max-width: 639px)').matches)

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value
}

// Шаг делает тот, кто уже вошёл: кнопка входа не нужна, только подсказка, что нажать
const isRightPerson = computed(() => Boolean(step.value?.user && step.value.user.id === demoPersona.value?.userId))
const needsLogin = computed(() => Boolean(step.value?.user) && !isRightPerson.value)
const isEvent = computed(() => step.value?.action === EVENT_ACTION)
const isWaiting = computed(() => step.value?.action === SYSTEM_ACTION)
// Запрет и прочее, что не видно автоматически, человек подтверждает сам
const isManual = computed(() => step.value?.action === FORBIDDEN_ACTION)

const stepText = computed(() => {
  if (!step.value) return ''

  const who = step.value.user?.fullName ?? t('sandbox.scenarios.system')

  return `${who} ${step.value.title}`
})

let timer = 0

async function pollStatus() {
  const id = run.applicationId.value

  if (!id) return

  try {
    const { data } = await applicationsService.fetchApplication($fetch, id)

    run.reportStatus(id, ApplicationMapper.toEntity(data.data).status)
  } catch {
    // Этому человеку заявка не видна (например, участнику) — шаг закроется действием или по кнопке
  }
}

function syncPolling() {
  window.clearInterval(timer)
  timer = 0

  if (run.scenario.value && !run.isFinished.value && run.applicationId.value) {
    timer = window.setInterval(pollStatus, POLL_MS)
  }
}

async function loginForStep() {
  if (!step.value) return

  try {
    await run.goToStep(step.value)
  } catch (err: unknown) {
    console.error('Scenario step login failed:', err)
    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('toast.loginError'), life: 4000 })
  }
}

async function applyStepEvent() {
  if (!step.value) return

  try {
    await run.applyEvent(step.value)
    toast.add({ severity: 'success', summary: t('toast.success'), detail: t('sandbox.scenarios.eventApplied'), life: 4000 })
  } catch (err: unknown) {
    console.error('Scenario step event failed:', err)
    toast.add({ severity: 'error', summary: t('toast.error'), detail: t('sandbox.scenarios.eventError'), life: 4000 })
  }
}

function confirmStep() {
  run.confirmCurrentStep()
}

function showSteps() {
  if (run.scenario.value) openPanel(run.scenario.value.id)
}

function finishScenario() {
  run.stop()
}

watch([() => run.scenario.value?.id, run.applicationId, run.isFinished], syncPolling, { immediate: true })
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <section
    v-if="run.scenario.value"
    class="w-80 max-w-[calc(100vw-5.5rem)] card-key p-3 sm:max-w-[calc(100vw-2rem)] sm:p-4"
    :aria-label="t('reviewer.tracker.label')"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="font-mono text-[11px] font-bold uppercase tracking-wider text-fino-text-muted">
        {{ t('reviewer.tracker.progress', { done: run.doneCount.value, total: run.steps.value.length }) }}
      </p>

      <button
        type="button"
        class="-mt-1 ml-auto flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg
               text-fino-text-muted transition-colors hover:bg-fino-surface-hover hover:text-fino-text
               focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
        :aria-label="isCollapsed ? t('reviewer.tracker.expand') : t('reviewer.tracker.collapse')"
        :aria-expanded="!isCollapsed"
        @click="toggleCollapsed"
      >
        <i
          :class="isCollapsed ? 'pi pi-chevron-up' : 'pi pi-chevron-down'"
          class="text-xs"
          aria-hidden="true"
        />
      </button>

      <button
        type="button"
        class="-mt-1 -mr-1 flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg
               text-fino-text-muted transition-colors hover:bg-fino-surface-hover hover:text-fino-text
               focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
        :aria-label="t('reviewer.tracker.stop')"
        :title="t('reviewer.tracker.stop')"
        @click="finishScenario"
      >
        <i
          class="pi pi-times text-xs"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Прогресс: сегмент на шаг, пройденные — красным, текущий — лаймом -->
    <div
      class="mt-2 flex gap-1"
      aria-hidden="true"
    >
      <span
        v-for="item in run.steps.value"
        :key="item.number"
        class="h-2 flex-1 rounded-full border border-fino-line transition-colors duration-500 motion-reduce:transition-none"
        :class="run.isStepDone(item) ? 'bg-primary' : run.isStepCurrent(item) ? 'bg-fino-lime' : 'bg-fino-surface'"
      />
    </div>

    <template v-if="step">
      <template v-if="!isCollapsed">
        <button
          type="button"
          class="mt-2 line-clamp-2 cursor-pointer text-left font-display text-base font-extrabold leading-tight
               text-fino-text underline-offset-4 hover:underline"
          @click="showSteps"
        >
          {{ run.scenario.value.title }}
        </button>

        <p
          :key="step.number"
          class="mt-2 text-sm leading-snug text-fino-text motion-safe:animate-fade-up"
          aria-live="polite"
        >
          <span class="font-mono text-xs font-bold">{{ t('reviewer.tracker.step', { number: step.number }) }}</span>
          {{ stepText }}
        </p>

        <!-- Что нажать в кабинете: у залогиненного человека шага -->
        <p
          v-if="!needsLogin && run.currentHint.value"
          class="mt-2 rounded-xl border-2 border-fino-line bg-fino-lime-soft px-3 py-2 text-xs font-semibold text-fino-text
               sm:text-sm"
        >
          <i
            :class="isWaiting ? 'pi pi-spinner pi-spin' : 'pi pi-hand-point-right'"
            class="mr-1 text-xs"
            aria-hidden="true"
          />
          {{ run.currentHint.value }}
        </p>
      </template>

      <button
        v-if="needsLogin"
        type="button"
        class="mt-3 inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-4
               text-sm font-bold text-primary-contrast btn-key disabled:cursor-not-allowed disabled:opacity-60
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="run.isBusy.value"
        @click="loginForStep"
      >
        {{ t('sandbox.scenarios.loginAs', { name: step.user?.fullName ?? '' }) }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </button>

      <button
        v-else-if="isEvent"
        type="button"
        class="mt-3 inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-4
               text-sm font-bold text-primary-contrast btn-key disabled:cursor-not-allowed disabled:opacity-60"
        :disabled="run.isBusy.value"
        @click="applyStepEvent"
      >
        {{ t('sandbox.scenarios.applyEvent') }}
      </button>

      <button
        v-else-if="isManual"
        type="button"
        class="mt-3 inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-fino-surface
               px-4 text-sm font-bold text-fino-text btn-key"
        @click="confirmStep"
      >
        {{ t('reviewer.tracker.confirm') }}
      </button>
    </template>

    <div
      v-else
      class="mt-3 flex flex-col gap-2"
    >
      <p class="rounded-xl border-2 border-fino-line bg-fino-lime px-3 py-2 text-sm font-bold text-[#111]">
        {{ t('reviewer.tracker.done') }}
      </p>

      <button
        type="button"
        class="cursor-pointer text-sm font-semibold text-fino-text-muted underline-offset-4 hover:text-fino-text
               hover:underline"
        @click="finishScenario"
      >
        {{ t('reviewer.tracker.finish') }}
      </button>
    </div>
  </section>
</template>
