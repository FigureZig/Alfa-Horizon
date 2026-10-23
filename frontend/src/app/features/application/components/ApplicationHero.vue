<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ApplicationProgress from './ApplicationProgress.vue'
import { ApplicationStatusToneEnum } from '@/app/types/application/application-status-tone-enum'
import type { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import type { ApplicationStatusViewInterface } from '@/app/types/application/application-status-view-interface'
import type { Nullable } from '@/app/types/nullable'

// Цвет несёт смысл: янтарный — нужно действие, зелёный — готово, красный — отказ, остальное нейтрально
const TONE_CLASSES: Record<ApplicationStatusToneEnum, string> = {
  [ApplicationStatusToneEnum.Neutral]: 'bg-fino-surface-secondary text-fino-text-muted',
  [ApplicationStatusToneEnum.Busy]: 'bg-fino-surface-secondary text-fino-text-muted',
  [ApplicationStatusToneEnum.Action]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  [ApplicationStatusToneEnum.Success]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [ApplicationStatusToneEnum.Danger]: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

const props = defineProps<{
  view: ApplicationStatusViewInterface
  // Номер шага в степпере; null — заявка закрыта, линейного пути нет
  step: Nullable<number>
  pendingAction: Nullable<ApplicationActionEnum>
  canWithdraw: boolean
}>()

const emit = defineEmits<{
  command: [action: ApplicationActionEnum]
  withdraw: []
}>()

const { t } = useI18n({ useScope: 'global' })

const toneClass = computed(() => TONE_CLASSES[props.view.tone])
const isBusy = computed(() => props.view.tone === ApplicationStatusToneEnum.Busy)
const isPending = computed(() => props.pendingAction !== null)
const isPrimaryPending = computed(() =>
  Boolean(props.view.primary?.command && props.pendingAction === props.view.primary.command),
)

const deadlineClass = computed(() =>
  props.view.isDeadlineUrgent
    ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400'
    : 'bg-fino-surface-secondary text-fino-text',
)

const hasActions = computed(() => Boolean(props.view.primary || props.view.secondary || props.canWithdraw))

function handlePrimaryCommand() {
  if (props.view.primary?.command) {
    emit('command', props.view.primary.command)
  }
}

function handleWithdraw() {
  emit('withdraw')
}
</script>

<template>
  <section
    class="flex flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-8"
    :aria-busy="isBusy"
  >
    <div class="flex items-start gap-4 sm:gap-5">
      <span
        class="flex size-12 shrink-0 items-center justify-center rounded-2xl transition-colors duration-300
               motion-reduce:transition-none sm:size-14"
        :class="toneClass"
        aria-hidden="true"
      >
        <i
          :class="view.icon"
          class="text-xl sm:text-2xl motion-reduce:animate-none"
        />
      </span>

      <div
        class="min-w-0 flex-1"
        aria-live="polite"
      >
        <h2 class="break-words text-xl font-bold tracking-tight text-balance text-fino-text sm:text-3xl">
          {{ view.title }}
        </h2>

        <p
          v-if="view.subtitle"
          class="mt-2 max-w-2xl break-words text-sm leading-relaxed text-fino-text-muted sm:text-base"
        >
          {{ view.subtitle }}
        </p>

        <p
          v-if="view.hint"
          class="mt-3 flex max-w-2xl items-start gap-2 break-words text-sm font-semibold leading-relaxed text-fino-text sm:text-base"
        >
          <i
            class="pi pi-arrow-right mt-1 text-xs text-primary"
            aria-hidden="true"
          />
          {{ view.hint }}
        </p>

        <p
          v-if="view.deadline"
          class="mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold sm:text-sm"
          :class="deadlineClass"
        >
          <i
            class="pi pi-clock text-xs"
            aria-hidden="true"
          />
          {{ view.deadline }}
        </p>

        <div
          v-if="hasActions"
          class="mt-5 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center"
        >
          <template v-if="view.primary">
            <RouterLink
              v-if="view.primary.to"
              :to="view.primary.to"
              class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm
                     font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90 active:scale-95
                     motion-reduce:transition-none
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              {{ view.primary.label }}
              <i
                class="pi pi-arrow-right text-xs"
                aria-hidden="true"
              />
            </RouterLink>

            <button
              v-else
              type="button"
              class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-5 py-3
                     text-sm font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90
                     active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              :disabled="isPending"
              :aria-busy="isPrimaryPending"
              @click="handlePrimaryCommand"
            >
              <i
                v-if="isPrimaryPending"
                class="pi pi-spinner pi-spin text-xs"
                aria-hidden="true"
              />
              {{ view.primary.label }}
            </button>
          </template>

          <RouterLink
            v-if="view.secondary?.to"
            :to="view.secondary.to"
            class="inline-flex min-h-12 items-center justify-center rounded-xl border border-fino-border px-5 py-3
                   text-sm font-semibold text-fino-text transition-colors hover:bg-fino-surface-hover
                   motion-reduce:transition-none"
          >
            {{ view.secondary.label }}
          </RouterLink>

          <button
            v-if="canWithdraw"
            type="button"
            class="cursor-pointer self-start py-2 text-sm font-semibold text-fino-text-muted transition-colors
                   hover:text-primary disabled:cursor-not-allowed disabled:opacity-60 sm:ml-auto sm:self-center
                   focus-visible:outline-2 focus-visible:outline-primary"
            :disabled="isPending"
            @click="handleWithdraw"
          >
            {{ t('application.actions.withdraw') }}
          </button>
        </div>
      </div>
    </div>

    <ApplicationProgress
      v-if="step !== null"
      :step="step"
      :substep="view.substep"
    />
  </section>
</template>
