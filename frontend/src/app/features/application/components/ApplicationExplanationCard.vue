<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationExplanationCardSkeleton from './ApplicationExplanationCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { ApplicationExplanationInterface } from '@/app/types/application/application-explanation-interface'
import type { Nullable } from '@/app/types/nullable'

const MAX_FACTORS = 4

const props = defineProps<{
  explanation: Nullable<ApplicationExplanationInterface>
  isLoading: boolean
  hasError: boolean
  // Специалисту путь к одобрению не нужен: это совет клиенту
  isPathHidden?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

// Свёрнуто по умолчанию; при отказе путь к одобрению важнее всего — раскрываем сразу
const isOpenByDefault = computed(() => props.explanation?.outcome === DecisionOutcomeEnum.Reject)

const isSkeletonVisible = computed(() => props.isLoading && !props.explanation)

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

const pathOptions = computed(() =>
  (props.explanation?.pathOptions ?? []).map((option) => ({
    title: option.title,
    summary: [
      t(`application.outcome.${option.outcome}`),
      option.amount === null ? '' : formatCurrency(option.amount, 'RUB'),
      option.rate === null ? '' : formatPercent(option.rate),
    ].filter(Boolean).join(' · '),
  })),
)

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <details
    class="group min-w-0 rounded-3xl border border-fino-border bg-fino-surface shadow-sm"
    :open="isOpenByDefault"
  >
    <summary
      class="flex cursor-pointer items-center justify-between gap-3 rounded-3xl px-5 py-4 marker:content-none
             focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span class="flex min-w-0 items-center gap-3">
        <span class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary">
          <i
            class="pi pi-question-circle"
            aria-hidden="true"
          />
        </span>

        <span class="min-w-0">
          <span class="block text-sm font-semibold text-fino-text">{{ t('application.explanation.title') }}</span>
          <span
            v-if="explanation?.score !== null && explanation?.riskClass"
            class="block text-xs text-fino-text-muted"
          >
            {{ t('application.explanation.summary', { score: explanation?.score, riskClass: explanation?.riskClass }) }}
          </span>
        </span>
      </span>

      <i
        class="pi pi-chevron-down shrink-0 text-xs text-fino-text-muted transition-transform duration-200
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
        <!-- Скоринг -->
        <div
          v-if="explanation.score !== null"
          class="flex items-center gap-4"
        >
          <p class="text-4xl font-bold tracking-tight text-fino-text">
            {{ explanation.score }}
          </p>

          <div>
            <p class="text-sm font-semibold text-fino-text">
              {{ t('application.explanation.score') }}
            </p>

            <p
              v-if="explanation.riskClass"
              class="text-xs text-fino-text-muted"
            >
              {{ t('application.explanation.riskClass', { riskClass: explanation.riskClass }) }}
            </p>
          </div>
        </div>

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

        <!-- Ставка из частей -->
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

        <!-- Чем ограничена сумма: сработавший лимит выделен -->
        <div v-if="explanation.caps.length">
          <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
            {{ t('application.explanation.limit') }}
          </p>

          <ul class="mt-2 flex flex-col gap-1.5 text-sm text-fino-text">
            <li
              v-for="cap in explanation.caps"
              :key="cap.code"
              class="flex items-start gap-2 break-words rounded-xl px-3 py-2"
              :class="cap.isBinding ? 'bg-fino-accent font-semibold text-primary' : 'text-fino-text-muted'"
            >
              <i
                :class="cap.isBinding ? 'pi pi-lock' : 'pi pi-minus'"
                class="mt-0.5 text-xs"
                aria-hidden="true"
              />
              <span class="min-w-0">{{ cap.text }}</span>
            </li>
          </ul>
        </div>

        <!-- Путь к одобрению -->
        <div v-if="!isPathHidden && (pathOptions.length || explanation.pathBlocked)">
          <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
            {{ explanation.pathTitle ?? t('application.explanation.path') }}
          </p>

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

              <p class="mt-0.5 text-xs text-fino-text-muted">
                {{ option.summary }}
              </p>
            </li>
          </ul>
        </div>
      </template>
    </div>
  </details>
</template>
