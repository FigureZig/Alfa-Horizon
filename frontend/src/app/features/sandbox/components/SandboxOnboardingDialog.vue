<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Dialog from 'primevue/dialog'

// Как пройти сценарий: четыре шага цикла «выбрал → вошёл → сделал → следующий шаг»
const STEPS = [
  { key: 'pick', icon: 'pi pi-compass', tone: 'bg-primary text-primary-contrast' },
  { key: 'login', icon: 'pi pi-sign-in', tone: 'bg-fino-violet text-white' },
  { key: 'act', icon: 'pi pi-check-square', tone: 'bg-fino-lime text-[#111]' },
  { key: 'next', icon: 'pi pi-forward', tone: 'bg-fino-blue text-white' },
] as const

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [visible: boolean]
  start: []
}>()

const { t } = useI18n({ useScope: 'global' })

function handleVisibleChange(visible: boolean) {
  emit('update:visible', visible)
}

function handleStart() {
  emit('update:visible', false)
  emit('start')
}

function handleClose() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="t('onboarding.title')"
    :style="{ width: '40rem', maxWidth: '94vw' }"
    @update:visible="handleVisibleChange"
  >
    <p class="text-sm leading-relaxed text-fino-text-muted">
      {{ t('onboarding.description') }}
    </p>

    <ol class="mt-5 flex flex-col gap-3">
      <li
        v-for="(step, index) in STEPS"
        :key="step.key"
        class="flex items-start gap-4 card-flat p-4 motion-safe:animate-fade-up"
        :style="{ animationDelay: `${index * 70}ms` }"
      >
        <span
          class="flex size-11 shrink-0 items-center justify-center rounded-2xl border-2 border-fino-line text-lg"
          :class="[step.tone, index % 2 ? 'rotate-3' : '-rotate-3']"
          aria-hidden="true"
        >
          <i :class="step.icon" />
        </span>

        <span class="min-w-0">
          <span class="block font-mono text-[11px] font-bold uppercase tracking-wider text-fino-text-muted">
            {{ t('onboarding.stepLabel', { number: index + 1 }) }}
          </span>
          <span class="mt-0.5 block font-display text-lg font-extrabold leading-tight text-fino-text">
            {{ t(`onboarding.steps.${step.key}.title`) }}
          </span>
          <span class="mt-1 block text-sm leading-relaxed text-fino-text-muted">
            {{ t(`onboarding.steps.${step.key}.text`) }}
          </span>
        </span>
      </li>
    </ol>

    <template #footer>
      <div class="flex w-full flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          class="min-h-11 cursor-pointer rounded-xl px-4 text-sm font-semibold text-fino-text-muted transition-colors
                 hover:bg-fino-surface-hover hover:text-fino-text motion-reduce:transition-none"
          @click="handleClose"
        >
          {{ t('onboarding.later') }}
        </button>

        <button
          type="button"
          class="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5
                 text-sm font-bold text-primary-contrast btn-key focus-visible:outline-2 focus-visible:outline-offset-2
                 focus-visible:outline-primary"
          @click="handleStart"
        >
          {{ t('onboarding.start') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </button>
      </div>
    </template>
  </Dialog>
</template>
