<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useReviewerPanel } from '@/app/composables/useReviewerPanel'

const { t } = useI18n({ useScope: 'global' })
const { activeScenario, doneStepNumber, openPanel, stopScenario } = useReviewerPanel()

const steps = computed(() => activeScenario.value?.steps ?? [])
const currentStep = computed(() => steps.value.find((step) => step.number === doneStepNumber.value) ?? null)
const nextStep = computed(() => steps.value.find((step) => step.number > doneStepNumber.value) ?? null)
const doneCount = computed(() => steps.value.filter((step) => step.number <= doneStepNumber.value).length)

// Что сделать в кабинете сейчас: «Елена Кравец подаёт заявку»
const currentText = computed(() => {
  if (!currentStep.value) return ''

  const who = currentStep.value.user?.fullName ?? t('sandbox.scenarios.system')

  return `${who} ${currentStep.value.title}`
})

function showNextStep() {
  if (activeScenario.value) openPanel(activeScenario.value.id)
}

function finishScenario() {
  stopScenario()
}
</script>

<template>
  <section
    v-if="activeScenario"
    class="w-80 max-w-[calc(100vw-2rem)] card-key p-4"
    :aria-label="t('reviewer.tracker.label')"
  >
    <div class="flex items-start justify-between gap-3">
      <p class="font-mono text-[11px] font-bold uppercase tracking-wider text-fino-text-muted">
        {{ t('reviewer.tracker.progress', { done: doneCount, total: steps.length }) }}
      </p>

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

    <p class="mt-1 line-clamp-2 font-display text-base font-extrabold leading-tight text-fino-text">
      {{ activeScenario.title }}
    </p>

    <!-- Прогресс сценария: сегмент на шаг, пройденные — красным -->
    <div
      class="mt-3 flex gap-1"
      aria-hidden="true"
    >
      <span
        v-for="step in steps"
        :key="step.number"
        class="h-2 flex-1 rounded-full border border-fino-line transition-colors duration-500 motion-reduce:transition-none"
        :class="step.number <= doneStepNumber ? 'bg-primary' : 'bg-fino-surface'"
      />
    </div>

    <p
      v-if="currentText"
      class="mt-3 text-sm leading-snug text-fino-text"
    >
      <span class="font-semibold">{{ t('reviewer.tracker.now') }}</span> {{ currentText }}
    </p>

    <button
      v-if="nextStep"
      type="button"
      class="mt-3 inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-4
             text-sm font-bold text-primary-contrast btn-key focus-visible:outline-2 focus-visible:outline-offset-2
             focus-visible:outline-primary"
      @click="showNextStep"
    >
      {{ t('reviewer.tracker.next', { number: nextStep.number }) }}
      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </button>

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
