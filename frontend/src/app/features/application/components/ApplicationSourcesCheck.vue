<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { useWorldClock } from '@/app/composables/useWorldClock'
import type { ApplicationEventInterface } from '@/app/types/application/application-event-interface'
import type { Nullable } from '@/app/types/nullable'

type GroupStatus = 'ok' | 'error' | 'empty'

interface SourceGroupInterface {
  key: string
  icon: string
  status: GroupStatus
}

const STEP_CHANGED = 'step.changed'
const STATUS_CHANGED = 'application.status_changed'
const DECISION_MADE = 'decision.made'
const SOURCES_STEP = 'sources'
const STATE_RUNNING = 'RUNNING'
const STATE_DONE = 'DONE'
const SOURCE_OK = 'ok'
const SOURCE_ERROR = 'error'
const SUBMITTED = 'SUBMITTED'
const SECOND_IN_MS = 1000
// Строки загораются по одной: так видно, что банк собрал сам. Время в заголовке — настоящее, из событий
const REVEAL_STEP_MS = 220
// Решение свежее — показываем проверку целиком и с анимацией; старое — одной строкой
const FRESH_WINDOW_MS = 60 * SECOND_IN_MS

// Источники бэкенда (policy/sources.yaml) человеческими группами: «налоговая», а не rsmp, sshr, paytax…
const SOURCE_GROUPS = [
  { key: 'registry', icon: 'pi pi-building', sources: ['egrul', 'egrip'] },
  { key: 'tax', icon: 'pi pi-percentage', sources: ['rsmp', 'sshr', 'paytax', 'debtam', 'snr'] },
  { key: 'accounting', icon: 'pi pi-file', sources: ['girbo'] },
  { key: 'bank', icon: 'pi pi-wallet', sources: ['bank_access', 'bank_charter', 'bank_tx'] },
  { key: 'credit', icon: 'pi pi-history', sources: ['bki', 'bki_info'] },
  { key: 'legal', icon: 'pi pi-shield', sources: ['legal'] },
  { key: 'contracts', icon: 'pi pi-briefcase', sources: ['eis'] },
  { key: 'poa', icon: 'pi pi-id-card', sources: ['mchd'] },
] as const

const STATUS_ICONS: Record<GroupStatus, string> = {
  ok: 'pi pi-check text-green-600 dark:text-green-400',
  error: 'pi pi-exclamation-triangle text-amber-600 dark:text-amber-400',
  empty: 'pi pi-minus text-fino-text-muted',
}

const props = defineProps<{
  events: ApplicationEventInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDuration } = useFormatters()
// События пишутся по часам мира, поэтому «свежесть» решения меряем ими же, а не часами браузера
const { now } = useWorldClock()

const revealedCount = ref(0)
const isExpanded = ref(false)
// Какую проверку уже показали: раскрываем каждую новую один раз, дальше решает человек
const handledCheckId = ref<Nullable<number>>(null)
let revealTimer: Nullable<ReturnType<typeof setInterval>> = null

// Последнее подходящее событие (lib проекта — ES2022, без Array.findLast)
function findLastEvent(predicate: (event: ApplicationEventInterface) => boolean): Nullable<ApplicationEventInterface> {
  for (let index = props.events.length - 1; index >= 0; index--) {
    if (predicate(props.events[index])) return props.events[index]
  }

  return null
}

function isSourcesStep(event: ApplicationEventInterface, state: string): boolean {
  return event.type === STEP_CHANGED && event.payload.step === SOURCES_STEP && event.payload.state === state
}

// Заявку могли перепроверить после события в реестре — берём последнюю проверку
const lastDone = computed(() => findLastEvent((event) => isSourcesStep(event, STATE_DONE)))

// Проверка идёт: последний старт шага позже последнего завершения
const isRunning = computed(() => {
  const running = findLastEvent((event) => isSourcesStep(event, STATE_RUNNING))

  if (!running) return false

  return !lastDone.value || new Date(running.at) > new Date(lastDone.value.at)
})

const statuses = computed<Record<string, string>>(() => {
  const sources = lastDone.value?.payload.sources

  return sources && typeof sources === 'object' ? (sources as Record<string, string>) : {}
})

const checkedCount = computed(() => Object.keys(statuses.value).length)

const groups = computed<SourceGroupInterface[]>(() =>
  SOURCE_GROUPS.flatMap((group) => {
    const values = group.sources.filter((source) => source in statuses.value).map((source) => statuses.value[source])

    if (!values.length) return []

    const status: GroupStatus = values.includes(SOURCE_ERROR)
      ? 'error'
      : values.includes(SOURCE_OK) ? 'ok' : 'empty'

    return [{ key: group.key, icon: group.icon, status }]
  }),
)

const hasErrors = computed(() => groups.value.some((group) => group.status === 'error'))

// От подачи до решения: столько клиент ждал ответа банка
const duration = computed(() => {
  if (!lastDone.value) return null

  const doneAt = new Date(lastDone.value.at).getTime()
  const submitted = findLastEvent((event) =>
    event.type === STATUS_CHANGED && event.payload.to === SUBMITTED && new Date(event.at).getTime() <= doneAt)
  const decision = props.events.find((event) => event.type === DECISION_MADE && new Date(event.at).getTime() >= doneAt)

  if (!submitted || !decision) return null

  return formatDuration((new Date(decision.at).getTime() - new Date(submitted.at).getTime()) / SECOND_IN_MS)
})

const title = computed(() => {
  if (isRunning.value) return t('application.sourcesCheck.running')

  return duration.value
    ? t('application.sourcesCheck.doneIn', { count: checkedCount.value, duration: duration.value }, checkedCount.value)
    : t('application.sourcesCheck.done', { count: checkedCount.value }, checkedCount.value)
})

const isFinished = computed(() => revealedCount.value >= groups.value.length)

function stopReveal() {
  if (revealTimer) clearInterval(revealTimer)
  revealTimer = null
}

function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function revealStep() {
  revealedCount.value += 1

  if (revealedCount.value >= groups.value.length) stopReveal()
}

function playReveal() {
  stopReveal()

  if (prefersReducedMotion()) {
    revealedCount.value = groups.value.length

    return
  }

  revealedCount.value = 0
  revealTimer = setInterval(revealStep, REVEAL_STEP_MS)
}

function isRevealed(index: number): boolean {
  return index < revealedCount.value
}

function toggleExpanded() {
  isExpanded.value = !isExpanded.value

  if (isExpanded.value) playReveal()
}

// Только что решили — раскрываем и проигрываем; открыли старую заявку — свёрнуто, по кнопке
function handleNewCheck() {
  const done = lastDone.value

  if (!done || now.value === null || handledCheckId.value === done.id) return

  handledCheckId.value = done.id

  const isFresh = now.value - new Date(done.at).getTime() < FRESH_WINDOW_MS

  isExpanded.value = isFresh

  if (isFresh) playReveal()
  else revealedCount.value = groups.value.length
}

watch([lastDone, now], handleNewCheck, { immediate: true })
onBeforeUnmount(stopReveal)
</script>

<template>
  <section
    v-if="isRunning || groups.length"
    class="card-key p-4 sm:p-5"
    :aria-busy="isRunning || !isFinished"
  >
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex min-w-0 items-center gap-3">
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary"
          aria-hidden="true"
        >
          <i :class="isRunning ? 'pi pi-spinner pi-spin' : 'pi pi-bolt'" />
        </span>

        <div class="min-w-0">
          <h2 class="break-words text-sm font-semibold text-fino-text sm:text-base">
            {{ title }}
          </h2>

          <p class="mt-0.5 text-xs text-fino-text-muted sm:text-sm">
            {{ t('application.sourcesCheck.subtitle') }}
          </p>
        </div>
      </div>

      <button
        v-if="groups.length"
        type="button"
        class="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-xl px-3 text-sm font-semibold text-primary
               transition-colors hover:bg-fino-surface-hover focus-visible:outline-2 focus-visible:outline-primary
               motion-reduce:transition-none"
        :aria-expanded="isExpanded"
        aria-controls="application-sources-list"
        @click="toggleExpanded"
      >
        {{ isExpanded ? t('application.sourcesCheck.hide') : t('application.sourcesCheck.show') }}
        <i
          class="pi pi-chevron-down text-xs transition-transform duration-200 motion-reduce:transition-none"
          :class="{ 'rotate-180': isExpanded }"
          aria-hidden="true"
        />
      </button>
    </div>

    <div
      v-if="isExpanded"
      id="application-sources-list"
      class="mt-4 border-t border-fino-border pt-4"
    >
      <ul class="grid grid-cols-1 gap-x-6 gap-y-2.5 sm:grid-cols-2">
        <li
          v-for="(group, index) in groups"
          :key="group.key"
          class="flex min-w-0 items-center gap-3 text-sm transition-opacity duration-200 motion-reduce:transition-none"
          :class="isRevealed(index) ? 'opacity-100' : 'opacity-40'"
        >
          <i
            :class="group.icon"
            class="w-4 shrink-0 text-center text-fino-text-muted"
            aria-hidden="true"
          />

          <span class="min-w-0 flex-1 break-words text-fino-text">
            {{ t(`application.sourcesCheck.groups.${group.key}`) }}
          </span>

          <span class="flex size-5 shrink-0 items-center justify-center">
            <i
              v-if="isRevealed(index)"
              :class="STATUS_ICONS[group.status]"
              class="animate-tick-pop text-sm motion-reduce:animate-none"
              aria-hidden="true"
            />
            <i
              v-else
              class="pi pi-spinner pi-spin text-xs text-fino-text-muted motion-reduce:animate-none"
              aria-hidden="true"
            />
          </span>

          <span class="sr-only">{{ t(`application.sourcesCheck.status.${group.status}`) }}</span>
        </li>
      </ul>

      <p
        v-if="isFinished"
        class="mt-4 text-xs leading-relaxed text-fino-text-muted sm:text-sm"
        role="status"
      >
        {{ hasErrors ? t('application.sourcesCheck.footerErrors') : t('application.sourcesCheck.footer') }}
      </p>
    </div>
  </section>
</template>
