<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Skeleton from 'primevue/skeleton'
import Toast from 'primevue/toast'
import { useSandboxWorld } from '@/app/composables/useSandboxWorld'
import { SandboxEventTypeEnum } from '@/app/types/sandbox/sandbox-event-type-enum'
import { SandboxFaultModeEnum } from '@/app/types/sandbox/sandbox-fault-mode-enum'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  inn?: string
  // Срок текущего шага заявки на экране: «Перемотать к сроку этого шага»
  deadlineAt?: Nullable<string>
}>()

const SECONDS_IN_HOUR = 3600
// Запас после срока: таймер банка закрывает шаг, когда срок уже прошёл
const DEADLINE_MARGIN_SECONDS = 60
const MS_IN_SECOND = 1000
// Свой канал уведомлений: общие тосты справа сверху закрывают заголовок открытой панели
const TOAST_GROUP = 'world'
const CLOCK_STEP_DAYS = [1, 7, 30]
const INN_PATTERN = /^(\d{10}|\d{12})$/
const AMOUNT_EVENT_TYPES: SandboxEventTypeEnum[] = [
  SandboxEventTypeEnum.TaxDebtAppeared,
  SandboxEventTypeEnum.ContractSigned,
]
const FAULT_SOURCES = [
  'egrul', 'egrip', 'rsmp', 'sshr', 'paytax', 'debtam', 'snr', 'girbo', 'legal',
  'bank_access', 'bank_charter', 'bank_tx', 'eis', 'mchd', 'bank_person', 'bki_info', 'bki', 'abs',
]

const { t, locale } = useI18n({ useScope: 'global' })
const toast = useToast()
const {
  clock,
  faults,
  isWorkerPaused,
  isLoading,
  error,
  loadWorld,
  advanceClock,
  createEvent,
  createFault,
  deleteFault,
  toggleWorker,
  resetWorld,
} = useSandboxWorld()

const isResetConfirmVisible = ref(false)
const isBusy = ref(false)

const eventType = ref<Nullable<SandboxEventTypeEnum>>(null)
const eventInn = ref(props.inn ?? '')
const eventAmount = ref<Nullable<number>>(null)

const faultSource = ref<Nullable<string>>(null)
const faultMode = ref<Nullable<SandboxFaultModeEnum>>(null)
const faultInn = ref('')

const eventTypeOptions = computed(() =>
  Object.entries(SandboxEventTypeEnum).map(([name, type]) => ({ type, label: t(`sandbox.world.eventTypes.${name}`) })),
)

const faultSourceOptions = computed(() =>
  FAULT_SOURCES.map((source) => ({ source, label: t(`sandbox.world.sources.${source}`) })),
)

const faultModeOptions = computed(() =>
  Object.values(SandboxFaultModeEnum).map((mode) => ({ mode, label: t(`sandbox.world.faultModes.${mode}`) })),
)

const isAmountRequired = computed(() => Boolean(eventType.value && AMOUNT_EVENT_TYPES.includes(eventType.value)))

const isEventInnValid = computed(() => INN_PATTERN.test(eventInn.value))
const isFaultInnValid = computed(() => !faultInn.value || INN_PATTERN.test(faultInn.value))

const isEventReady = computed(() =>
  Boolean(eventType.value) && isEventInnValid.value && (!isAmountRequired.value || Boolean(eventAmount.value)),
)
const isFaultReady = computed(() => Boolean(faultSource.value && faultMode.value) && isFaultInnValid.value)

const clockToday = computed(() =>
  clock.value
    ? new Intl.DateTimeFormat(locale.value, { dateStyle: 'long' }).format(new Date(clock.value.today))
    : '',
)
const isClockShifted = computed(() => Boolean(clock.value?.offsetSeconds))

// Сколько перемотать до срока шага по часам мира; срок уже прошёл — перематывать нечего
const secondsToDeadline = computed(() => {
  if (!props.deadlineAt || !clock.value) return 0

  const seconds = (new Date(props.deadlineAt).getTime() - new Date(clock.value.now).getTime()) / MS_IN_SECOND

  return seconds > 0 ? Math.ceil(seconds) + DEADLINE_MARGIN_SECONDS : 0
})

const deadlineDate = computed(() =>
  props.deadlineAt
    ? new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
      .format(new Date(props.deadlineAt))
    : '',
)

/**
 * Выполняет команду мира: блокирует кнопки на время запроса и показывает результат уведомлением.
 */
async function runCommand(command: () => Promise<void>, successKey: string) {
  if (isBusy.value) return false

  isBusy.value = true

  try {
    await command()

    toast.add({
      severity: 'success',
      group: TOAST_GROUP,
      summary: t('toast.success'),
      detail: t(successKey),
      life: 3000,
    })

    return true
  } catch (err: unknown) {
    console.error('Sandbox world command failed:', err)

    toast.add({
      severity: 'error',
      group: TOAST_GROUP,
      summary: t('toast.error'),
      detail: t('sandbox.world.commandError'),
      life: 4000,
    })

    return false
  } finally {
    isBusy.value = false
  }
}

function handleAdvanceHours() {
  runCommand(() => advanceClock({ advance_s: SECONDS_IN_HOUR }), 'sandbox.world.clock.advanced')
}

function handleAdvanceDays(days: number) {
  runCommand(() => advanceClock({ advance_days: days }), 'sandbox.world.clock.advanced')
}

function handleAdvanceToDeadline() {
  if (!secondsToDeadline.value) return

  runCommand(() => advanceClock({ advance_s: secondsToDeadline.value }), 'sandbox.world.clock.toDeadlineDone')
}

function handleResetClock() {
  runCommand(() => advanceClock({ reset: true }), 'sandbox.world.clock.restored')
}

async function handleCreateEvent() {
  if (!eventType.value || !isEventReady.value) return

  const type = eventType.value
  const amount = isAmountRequired.value ? (eventAmount.value ?? undefined) : undefined

  await runCommand(() => createEvent({ type, inn: eventInn.value, amount }), 'sandbox.world.events.applied')
}

async function handleCreateFault() {
  if (!faultSource.value || !faultMode.value || !isFaultReady.value) return

  const source = faultSource.value
  const mode = faultMode.value
  const inn = faultInn.value || undefined

  await runCommand(() => createFault({ source, mode, inn }), 'sandbox.world.faults.created')
}

function handleDeleteFault(faultId: string) {
  runCommand(() => deleteFault(faultId), 'sandbox.world.faults.removed')
}

function handleToggleWorker() {
  runCommand(
    toggleWorker,
    isWorkerPaused.value ? 'sandbox.world.worker.resumed' : 'sandbox.world.worker.paused',
  )
}

function openResetConfirm() {
  isResetConfirmVisible.value = true
}

function cancelReset() {
  isResetConfirmVisible.value = false
}

async function confirmReset() {
  isResetConfirmVisible.value = false

  await runCommand(resetWorld, 'sandbox.world.reset.done')
}

function faultLabel(source: string) {
  return FAULT_SOURCES.includes(source) ? t(`sandbox.world.sources.${source}`) : source
}

// Данные мира читаем при открытии вкладки: их мог поменять другой экран или вкладка
onMounted(loadWorld)

watch(() => props.inn, (inn) => {
  if (inn) eventInn.value = inn
})
</script>

<template>
  <Toast
    :group="TOAST_GROUP"
    position="bottom-left"
  />

  <div class="flex flex-col gap-6">
    <p class="text-sm leading-relaxed text-fino-text-muted">
      {{ t('sandbox.world.description') }}
    </p>

    <Message
      v-if="error"
      severity="error"
      size="small"
    >
      <div class="flex flex-wrap items-center gap-3">
        <span>{{ t('sandbox.world.loadError') }}</span>

        <button
          type="button"
          class="cursor-pointer font-semibold underline"
          @click="loadWorld"
        >
          {{ t('common.retry') }}
        </button>
      </div>
    </Message>

    <!-- Часы -->
    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-bold text-fino-text">
        {{ t('sandbox.world.clock.title') }}
      </h3>

      <Skeleton
        v-if="isLoading && !clock"
        height="1.5rem"
        width="12rem"
      />
      <p
        v-else-if="clock"
        class="text-sm text-fino-text-muted"
      >
        {{ t('sandbox.world.clock.today', { date: clockToday }) }}
      </p>

      <!-- Симуляция у объекта: срок этого шага заявки, как Run simulation у Stripe -->
      <button
        v-if="secondsToDeadline"
        type="button"
        class="flex cursor-pointer items-center gap-3 rounded-2xl border border-amber-500/30 bg-amber-500/10 px-4 py-3
               text-left transition-colors hover:bg-amber-500/15 disabled:cursor-not-allowed disabled:opacity-50
               motion-reduce:transition-none"
        :disabled="isBusy"
        @click="handleAdvanceToDeadline"
      >
        <i
          class="pi pi-forward text-amber-700 dark:text-amber-400"
          aria-hidden="true"
        />
        <span class="min-w-0">
          <span class="block text-sm font-semibold text-fino-text">{{ t('sandbox.world.clock.toDeadline') }}</span>
          <span class="block text-xs text-fino-text-muted">{{ t('sandbox.world.clock.toDeadlineHint', { date: deadlineDate }) }}</span>
        </span>
      </button>

      <div class="flex flex-wrap gap-2">
        <button
          type="button"
          class="cursor-pointer rounded-xl border border-fino-border px-3 py-2 text-sm font-semibold
                   text-fino-text transition-colors hover:bg-fino-surface-hover
                   disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
          :disabled="isBusy"
          @click="handleAdvanceHours"
        >
          {{ t('sandbox.world.clock.plusHour') }}
        </button>

        <button
          v-for="days in CLOCK_STEP_DAYS"
          :key="days"
          type="button"
          class="cursor-pointer rounded-xl border border-fino-border px-3 py-2 text-sm font-semibold
                   text-fino-text transition-colors hover:bg-fino-surface-hover
                   disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
          :disabled="isBusy"
          @click="handleAdvanceDays(days)"
        >
          {{ t('sandbox.world.clock.plusDays', { count: days }) }}
        </button>

        <button
          type="button"
          class="cursor-pointer rounded-xl px-3 py-2 text-sm font-semibold text-primary
                   transition-colors hover:bg-fino-accent
                   disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
          :disabled="isBusy || !isClockShifted"
          @click="handleResetClock"
        >
          {{ t('sandbox.world.clock.restore') }}
        </button>
      </div>
    </section>

    <!-- События реестров -->
    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-bold text-fino-text">
        {{ t('sandbox.world.events.title') }}
      </h3>

      <Select
        v-model="eventType"
        :options="eventTypeOptions"
        option-label="label"
        option-value="type"
        :placeholder="t('sandbox.world.events.typePlaceholder')"
        :aria-label="t('sandbox.world.events.typePlaceholder')"
        :disabled="isBusy"
        fluid
      />

      <InputText
        v-model="eventInn"
        inputmode="numeric"
        :maxlength="12"
        :placeholder="t('sandbox.world.innPlaceholder')"
        :aria-label="t('sandbox.world.innPlaceholder')"
        :invalid="Boolean(eventInn) && !isEventInnValid"
        :disabled="isBusy"
        fluid
      />

      <InputNumber
        v-if="isAmountRequired"
        v-model="eventAmount"
        :min="1"
        :max-fraction-digits="0"
        :locale="locale"
        suffix=" ₽"
        :placeholder="t('sandbox.world.events.amountPlaceholder')"
        :aria-label="t('sandbox.world.events.amountPlaceholder')"
        :disabled="isBusy"
        fluid
      />

      <button
        type="button"
        class="cursor-pointer rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold
                 text-primary-contrast transition-opacity hover:opacity-90
                 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        :disabled="isBusy || !isEventReady"
        @click="handleCreateEvent"
      >
        {{ t('sandbox.world.events.apply') }}
      </button>
    </section>

    <!-- Отказы источников -->
    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-bold text-fino-text">
        {{ t('sandbox.world.faults.title') }}
      </h3>

      <Select
        v-model="faultSource"
        :options="faultSourceOptions"
        option-label="label"
        option-value="source"
        :placeholder="t('sandbox.world.faults.sourcePlaceholder')"
        :aria-label="t('sandbox.world.faults.sourcePlaceholder')"
        :disabled="isBusy"
        fluid
      />

      <Select
        v-model="faultMode"
        :options="faultModeOptions"
        option-label="label"
        option-value="mode"
        :placeholder="t('sandbox.world.faults.modePlaceholder')"
        :aria-label="t('sandbox.world.faults.modePlaceholder')"
        :disabled="isBusy"
        fluid
      />

      <InputText
        v-model="faultInn"
        inputmode="numeric"
        :maxlength="12"
        :placeholder="t('sandbox.world.faults.innPlaceholder')"
        :aria-label="t('sandbox.world.faults.innPlaceholder')"
        :invalid="!isFaultInnValid"
        :disabled="isBusy"
        fluid
      />

      <button
        type="button"
        class="cursor-pointer rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold
                 text-primary-contrast transition-opacity hover:opacity-90
                 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        :disabled="isBusy || !isFaultReady"
        @click="handleCreateFault"
      >
        {{ t('sandbox.world.faults.create') }}
      </button>

      <p
        v-if="!faults.length && !isLoading"
        class="text-sm text-fino-text-muted"
      >
        {{ t('sandbox.world.faults.empty') }}
      </p>

      <ul
        v-else
        class="flex flex-col gap-2"
      >
        <li
          v-for="fault in faults"
          :key="fault.id"
          class="flex items-center justify-between gap-3 rounded-xl bg-fino-surface-secondary px-3 py-2"
        >
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-fino-text">
              {{ faultLabel(fault.source) }}
            </p>

            <p class="truncate text-xs text-fino-text-muted">
              {{ t(`sandbox.world.faultModes.${fault.mode}`) }} ·
              {{ fault.inn ?? t('sandbox.world.faults.allCompanies') }}
            </p>
          </div>

          <button
            type="button"
            class="flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg
                     text-fino-text-muted transition-colors hover:bg-fino-surface-hover hover:text-fino-text
                     disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
            :aria-label="t('sandbox.world.faults.remove')"
            :title="t('sandbox.world.faults.remove')"
            :disabled="isBusy"
            @click="handleDeleteFault(fault.id)"
          >
            <i
              class="pi pi-times"
              aria-hidden="true"
            />
          </button>
        </li>
      </ul>
    </section>

    <!-- Воркер -->
    <section class="flex flex-col gap-3">
      <h3 class="text-sm font-bold text-fino-text">
        {{ t('sandbox.world.worker.title') }}
      </h3>

      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ isWorkerPaused ? t('sandbox.world.worker.pausedHint') : t('sandbox.world.worker.runningHint') }}
      </p>

      <button
        type="button"
        class="cursor-pointer rounded-xl border border-fino-border px-4 py-2.5 text-sm font-semibold
                 text-fino-text transition-colors hover:bg-fino-surface-hover
                 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        :disabled="isBusy"
        @click="handleToggleWorker"
      >
        {{ isWorkerPaused ? t('sandbox.world.worker.resume') : t('sandbox.world.worker.pause') }}
      </button>
    </section>

    <!-- Сброс -->
    <section class="flex flex-col gap-3 border-t border-fino-border pt-6">
      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ t('sandbox.world.reset.hint') }}
      </p>

      <button
        type="button"
        class="cursor-pointer rounded-xl border border-red-500/40 px-4 py-2.5 text-sm font-semibold
                 text-red-600 transition-colors hover:bg-red-500/10 dark:text-red-400
                 disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none"
        :disabled="isBusy"
        @click="openResetConfirm"
      >
        {{ t('sandbox.world.reset.action') }}
      </button>
    </section>
  </div>

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
</template>
