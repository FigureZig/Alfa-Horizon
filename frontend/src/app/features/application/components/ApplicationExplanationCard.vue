<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationExplanationCardSkeleton from './ApplicationExplanationCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { ApplicationExplanationInterface } from '@/app/types/application/application-explanation-interface'
import type { DataSourceEnum } from '@/app/types/company/data-source-enum'
import type { Nullable } from '@/app/types/nullable'

const MAX_FACTORS = 4
const MAX_REASONS = 4
// Причины-лимиты показывает блок «Почему такая сумма»
const CAP_REASON_KIND = 'cap'
// Лимит платежей зависит от других кредитов — их банк узнаёт из кредитной истории
const PAYMENT_CAP = 'CAP_PAYMENT_CAPACITY'
// Факторы оценки, которые считаются по кредитной истории
const BKI_FACTORS = ['F4_debt_load', 'F5_delinquency', 'F6_credit_hunger']
const PERCENT_MAX = 100

const props = defineProps<{
  explanation: Nullable<ApplicationExplanationInterface>
  isLoading: boolean
  hasError: boolean
  // Специалисту путь к одобрению не нужен: это совет клиенту
  isPathHidden?: boolean
  // Сколько просили — для полосы «дают / предел / просили»
  requestedAmount?: Nullable<number>
  // Сколько показывал подбор до заявки: если банк дал меньше, объясняем почему
  shownAmount?: Nullable<number>
  // Условия предварительные: кредитной истории ещё нет
  isProvisional?: boolean
  // Откуда банк взял данные — для экспертов
  sources?: DataSourceEnum[]
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatMoney, formatPercent, formatList } = useFormatters()

const outcome = computed(() => props.explanation?.outcome ?? null)
const isSkeletonVisible = computed(() => props.isLoading && !props.explanation)

// При отказе путь к одобрению важнее всего — раскрываем сразу
const isOpenByDefault = computed(() => outcome.value === DecisionOutcomeEnum.Reject && !props.isPathHidden)

const bindingCap = computed(() => props.explanation?.caps.find((cap) => cap.isBinding) ?? null)
const otherCaps = computed(() => props.explanation?.caps.filter((cap) => !cap.isBinding && cap.value !== null) ?? [])

function lowerFirst(text: string): string {
  return text ? text.charAt(0).toLowerCase() + text.slice(1) : text
}

function capitalize(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

// «Ставка 21,7 %: ключевая 14 % + отрасль 5,7 % + риск 2 %»
const priceLine = computed(() => {
  const explanation = props.explanation

  if (!explanation?.rate || !explanation.priceParts.length) return ''

  return t('application.explanation.level1.price', {
    rate: formatPercent(explanation.rate),
    parts: explanation.priceParts
      .map((part) => t(`application.explanation.partShort.${part.part}`, { value: formatPercent(part.value) }))
      .join(' + '),
  })
})

const firstReason = computed(() =>
  props.explanation?.reasons.find((reason) => reason.kind !== CAP_REASON_KIND) ?? null,
)

// Первый уровень — одна строка «почему» с цифрами; что делать, говорит шапка заявки
const levelOne = computed(() => {
  const explanation = props.explanation

  if (!explanation) return ''

  switch (explanation.outcome) {
    case DecisionOutcomeEnum.Approve:
      return priceLine.value
    case DecisionOutcomeEnum.CounterOffer:
      return bindingCap.value
        ? t('application.explanation.level1.capped', { rule: lowerFirst(bindingCap.value.title) })
        : priceLine.value
    case DecisionOutcomeEnum.Reject:
      if (props.isPathHidden) return firstReason.value?.text ?? ''

      return explanation.pathBlocked || !explanation.pathOptions.length
        ? t('application.explanation.level1.rejectFinal')
        : t('application.explanation.level1.rejectFixable', explanation.pathOptions.length)
    default:
      return firstReason.value?.text ?? priceLine.value
  }
})

// Граница объяснения: решение без кредитной истории называем прямо
const isWithoutBki = computed(() =>
  Boolean(props.isProvisional)
  || Boolean(props.explanation?.missingFactors.some((factor) => BKI_FACTORS.includes(factor))),
)

// Подбор показывал больше, чем дал банк: говорим, откуда разница
const shownNote = computed(() => {
  const { shownAmount, requestedAmount } = props
  const limitAmount = props.explanation?.limitAmount

  if (!shownAmount || !limitAmount || limitAmount >= shownAmount) return ''
  if (requestedAmount && limitAmount >= requestedAmount) return ''

  return bindingCap.value?.code === PAYMENT_CAP && !isWithoutBki.value
    ? t('application.explanation.shownLowerBki', { shown: formatMoney(shownAmount) })
    : t('application.explanation.shownLower', { shown: formatMoney(shownAmount) })
})

// Почему такая сумма: правило, его предел и итог с запасом — только если банк дал меньше, чем просили
const capSummary = computed(() => {
  const cap = bindingCap.value
  const limitAmount = props.explanation?.limitAmount
  const requested = props.requestedAmount

  if (!cap || cap.value === null || !limitAmount || !requested || limitAmount >= requested) return null

  return {
    title: cap.title,
    value: formatMoney(cap.value),
    // Цифры обязаны сходиться: предел 3 862 518 ₽, а дают 3 200 000 ₽ — объясняем разницу
    result: limitAmount && limitAmount < cap.value
      ? t('application.explanation.capResult', { amount: formatMoney(limitAmount) })
      : '',
  }
})

// Полоса «дают / предел / просили» — где упирается сумма
const amountBar = computed(() => {
  const cap = bindingCap.value
  const limitAmount = props.explanation?.limitAmount
  const requested = props.requestedAmount

  if (outcome.value !== DecisionOutcomeEnum.CounterOffer || !cap?.value || !limitAmount || !requested) return null

  const max = Math.max(requested, cap.value)

  return {
    offeredWidth: `${Math.min((limitAmount / max) * PERCENT_MAX, PERCENT_MAX)}%`,
    capPosition: `${Math.min((cap.value / max) * PERCENT_MAX, PERCENT_MAX)}%`,
    offered: formatMoney(limitAmount),
    cap: formatMoney(cap.value),
    requested: formatMoney(requested),
  }
})

const reasons = computed(() =>
  (props.explanation?.reasons ?? [])
    .filter((reason) => reason.kind !== CAP_REASON_KIND)
    .slice(0, MAX_REASONS),
)

const pathOptions = computed(() =>
  (props.explanation?.pathOptions ?? []).map((option) => {
    const amount = option.amount === null ? '' : formatMoney(option.amount)
    const rate = option.rate === null ? '' : formatPercent(option.rate)
    const verb = option.outcome === DecisionOutcomeEnum.Approve ? 'approve' : 'offer'
    const resultKey = rate ? verb : `${verb}NoRate`

    return {
      title: capitalize(option.title),
      result: amount
        ? t(`application.explanation.pathResult.${resultKey}`, { amount, rate })
        : t(`application.outcome.${option.outcome}`),
    }
  }),
)

const isPathVisible = computed(() =>
  !props.isPathHidden && Boolean(pathOptions.value.length || props.explanation?.pathBlocked),
)

// Третий уровень — для экспертов: риск словами, балл, факторы, ставка по частям, источники
const riskLine = computed(() => {
  const explanation = props.explanation

  if (!explanation?.riskClass || explanation.score === null) return ''

  return t('application.explanation.riskLine', {
    risk: t(`application.explanation.risk.${explanation.riskClass}`),
    riskClass: explanation.riskClass,
    score: explanation.score,
  })
})

// Сначала факторы, которые тянут оценку вниз, затем самые весомые плюсы
const factors = computed(() =>
  [...(props.explanation?.factors ?? [])]
    .filter((factor) => factor.effect === 'minus' || factor.effect === 'plus')
    .sort((a, b) => a.points - b.points)
    .slice(0, MAX_FACTORS)
    .map((factor) => ({
      ...factor,
      points: factor.points > 0 ? `+${factor.points}` : String(factor.points),
      isMinus: factor.effect === 'minus',
      gain: factor.gain ? t('application.explanation.gain', { gain: factor.gain }) : '',
    })),
)

const priceParts = computed(() =>
  (props.explanation?.priceParts ?? []).map((part) => ({
    part: part.part,
    label: t(`application.explanation.pricePart.${part.part}`),
    value: formatPercent(part.value),
  })),
)

const sourcesLine = computed(() =>
  props.sources?.length
    ? formatList(props.sources.map((source) => t(`companyInsights.source.${source}`)))
    : '',
)

const hasExpertDetails = computed(() => Boolean(riskLine.value || factors.value.length || priceParts.value.length))

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <details
    class="group min-w-0 rounded-3xl border border-fino-border bg-fino-surface shadow-sm"
    :open="isOpenByDefault"
  >
    <!-- Первый уровень: всегда видно — почему, одной строкой с цифрами, и границы объяснения -->
    <summary
      class="flex cursor-pointer items-start justify-between gap-3 rounded-3xl px-5 py-4 marker:content-none
             focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span class="flex min-w-0 items-start gap-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary">
          <i
            class="pi pi-question-circle"
            aria-hidden="true"
          />
        </span>

        <span class="min-w-0">
          <span class="block text-sm font-semibold text-fino-text">{{ t('application.explanation.title') }}</span>

          <span
            v-if="levelOne"
            class="mt-1 block break-words text-sm text-fino-text"
          >{{ levelOne }}</span>

          <span
            v-if="isWithoutBki"
            class="mt-1.5 flex items-start gap-1.5 text-xs text-amber-700 dark:text-amber-400"
          >
            <i
              class="pi pi-info-circle mt-0.5 text-[11px]"
              aria-hidden="true"
            />
            <span class="min-w-0 break-words">{{ t('application.explanation.withoutBki') }}</span>
          </span>

          <span
            v-if="shownNote"
            class="mt-1.5 block break-words text-xs text-fino-text-muted"
          >{{ shownNote }}</span>
        </span>
      </span>

      <i
        class="pi pi-chevron-down mt-3 shrink-0 text-xs text-fino-text-muted transition-transform duration-200
               group-open:rotate-180 motion-reduce:transition-none"
        aria-hidden="true"
      />
    </summary>

    <div class="flex flex-col gap-5 px-5 pb-5">
      <ApplicationExplanationCardSkeleton v-if="isSkeletonVisible" />

      <AppErrorState
        v-else-if="hasError"
        :message="t('application.explanation.loadError')"
        is-inline
        @retry="handleRetry"
      />

      <template v-else-if="explanation">
        <!-- Второй уровень: почему такая сумма, причины и что сделать -->
        <section v-if="capSummary">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
            {{ t('application.explanation.limit') }}
          </h3>

          <div class="mt-2 rounded-xl bg-fino-surface-secondary p-3">
            <p class="break-words text-sm font-semibold text-fino-text">
              {{ capSummary.title }}
            </p>
            <p class="mt-0.5 text-sm text-fino-text-muted">
              {{ t('application.explanation.capValue', { amount: capSummary.value }) }}
            </p>
            <p
              v-if="capSummary.result"
              class="mt-0.5 text-sm text-fino-text-muted"
            >
              {{ capSummary.result }}
            </p>
          </div>

          <!-- Где упирается сумма: дают, предел правила и сколько просили -->
          <div
            v-if="amountBar"
            class="mt-3"
          >
            <div
              class="relative h-2.5 rounded-full bg-fino-surface-secondary"
              aria-hidden="true"
            >
              <div
                class="absolute inset-y-0 left-0 rounded-full bg-green-500"
                :style="{ width: amountBar.offeredWidth }"
              />
              <div
                class="absolute -top-1 -bottom-1 w-0.5 rounded-full bg-fino-text"
                :style="{ left: amountBar.capPosition }"
              />
            </div>

            <dl class="mt-2 grid grid-cols-3 gap-2 text-xs">
              <div>
                <dt class="flex items-center gap-1 text-fino-text-muted">
                  <span
                    class="size-2 rounded-full bg-green-500"
                    aria-hidden="true"
                  />
                  {{ t('application.explanation.bar.offered') }}
                </dt>
                <dd class="font-semibold text-fino-text">
                  {{ amountBar.offered }}
                </dd>
              </div>
              <div>
                <dt class="flex items-center gap-1 text-fino-text-muted">
                  <span
                    class="h-2.5 w-0.5 rounded-full bg-fino-text"
                    aria-hidden="true"
                  />
                  {{ t('application.explanation.bar.cap') }}
                </dt>
                <dd class="font-semibold text-fino-text">
                  {{ amountBar.cap }}
                </dd>
              </div>
              <div class="text-right">
                <dt class="text-fino-text-muted">
                  {{ t('application.explanation.bar.requested') }}
                </dt>
                <dd class="font-semibold text-fino-text">
                  {{ amountBar.requested }}
                </dd>
              </div>
            </dl>
          </div>

          <ul
            v-if="otherCaps.length"
            class="mt-2 flex flex-col gap-1"
          >
            <li
              v-for="cap in otherCaps"
              :key="cap.code"
              class="break-words text-xs text-fino-text-muted"
            >
              {{ cap.text }}
            </li>
          </ul>
        </section>

        <section v-if="reasons.length">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
            {{ t('application.explanation.reasons') }}
          </h3>

          <ul class="mt-2 flex flex-col gap-1.5">
            <li
              v-for="reason in reasons"
              :key="reason.code"
              class="flex items-start gap-2 break-words text-sm text-fino-text"
            >
              <i
                class="pi pi-circle-fill mt-1.5 text-[6px] text-fino-text-muted"
                aria-hidden="true"
              />
              <span class="min-w-0">{{ reason.text }}</span>
            </li>
          </ul>
        </section>

        <!-- Что сделать — действие и результат -->
        <section v-if="isPathVisible">
          <h3 class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
            {{ explanation.pathTitle ?? t('application.explanation.path') }}
          </h3>

          <p
            v-if="explanation.pathBlocked"
            class="mt-2 text-sm text-fino-text-muted"
          >
            {{ t('application.explanation.pathBlocked') }}
          </p>

          <ul
            v-else
            class="mt-2 flex flex-col gap-2"
          >
            <li
              v-for="option in pathOptions"
              :key="option.title"
              class="rounded-xl bg-fino-surface-secondary p-3 text-sm"
            >
              <p class="break-words font-semibold text-fino-text">
                {{ option.title }}
              </p>

              <p class="mt-0.5 flex items-center gap-1.5 text-xs text-fino-text-muted">
                <i
                  class="pi pi-arrow-right text-[10px] text-primary"
                  aria-hidden="true"
                />
                {{ option.result }}
              </p>
            </li>
          </ul>
        </section>

        <p class="text-xs leading-relaxed text-fino-text-muted">
          {{ t('application.explanation.boundary') }}
        </p>

        <!-- Третий уровень: для любопытных и специалистов -->
        <details
          v-if="hasExpertDetails"
          class="group/expert rounded-2xl border border-fino-border"
        >
          <summary
            class="flex cursor-pointer items-center justify-between gap-3 rounded-2xl px-4 py-3 text-sm font-semibold
                   text-fino-text marker:content-none focus-visible:outline-2 focus-visible:outline-primary"
          >
            {{ t('application.explanation.expert') }}
            <i
              class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
                     group-open/expert:rotate-180 motion-reduce:transition-none"
              aria-hidden="true"
            />
          </summary>

          <div class="flex flex-col gap-4 px-4 pb-4">
            <p
              v-if="riskLine"
              class="text-sm font-semibold text-fino-text"
            >
              {{ riskLine }}
            </p>

            <ul
              v-if="factors.length"
              class="flex flex-col divide-y divide-fino-border"
            >
              <li
                v-for="factor in factors"
                :key="factor.factor"
                class="flex items-start justify-between gap-3 py-2 first:pt-0 last:pb-0"
              >
                <div class="min-w-0">
                  <p class="break-words text-sm text-fino-text">
                    {{ factor.title }}
                  </p>

                  <p
                    v-if="factor.text || factor.gain"
                    class="mt-0.5 break-words text-xs text-fino-text-muted"
                  >
                    {{ factor.text }} {{ factor.gain }}
                  </p>
                </div>

                <span
                  class="shrink-0 text-sm font-semibold"
                  :class="factor.isMinus ? 'text-red-700 dark:text-red-400' : 'text-green-700 dark:text-green-400'"
                >
                  {{ factor.points }}
                </span>
              </li>
            </ul>

            <div v-if="priceParts.length">
              <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
                {{ t('application.explanation.price') }}
              </p>

              <dl class="mt-2 flex flex-col gap-1.5 text-sm">
                <div
                  v-for="part in priceParts"
                  :key="part.part"
                  class="flex justify-between gap-3"
                >
                  <dt class="text-fino-text-muted">
                    {{ part.label }}
                  </dt>
                  <dd class="font-semibold text-fino-text">
                    {{ part.value }}
                  </dd>
                </div>
              </dl>
            </div>

            <p
              v-if="sourcesLine"
              class="flex items-start gap-1.5 text-xs text-fino-text-muted"
            >
              <i
                class="pi pi-database mt-0.5 text-xs"
                aria-hidden="true"
              />
              <span class="min-w-0 break-words">{{ t('application.explanation.sources', { list: sourcesLine }) }}</span>
            </p>
          </div>
        </details>
      </template>
    </div>
  </details>
</template>
