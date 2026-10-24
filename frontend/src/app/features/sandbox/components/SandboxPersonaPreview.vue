<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import SandboxPersonaPreviewProduct from './SandboxPersonaPreviewProduct.vue'
import SandboxPersonaPreviewSkeleton from './SandboxPersonaPreviewSkeleton.vue'
import AppErrorState from '@/app/components/AppErrorState.vue'
import { useAnimatedNumber } from '@/app/composables/useAnimatedNumber'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaPreviewInterface } from '@/app/types/sandbox/sandbox-persona-preview-interface'

// Шкала балла для полоски: от самого низкого класса до верха карты
const SCORE_MIN = 300
const SCORE_MAX = 850
const JOINT_SIGNING = 'joint'
// Нормы закона в скобках — только во всплывающей подсказке
const LAW_REFERENCE_PATTERN = /\s*\([^()]*(?:ст\.|ФЗ|ГК)[^()]*\)/g

const props = defineProps<{
  preview: Nullable<SandboxPersonaPreviewInterface>
  isLoading: boolean
  hasError: boolean
  // В компании есть представитель по доверенности: при совместной подписи объясняем, почему он не подпишет
  hasRepresentative: boolean
}>()

const emit = defineEmits<{
  highlight: [fields: string[]]
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })

const animatedScore = useAnimatedNumber(() => props.preview?.score ?? null)

const isStopped = computed(() => Boolean(props.preview?.blockers.length))

const scoreWidth = computed(() => {
  const score = animatedScore.value ?? SCORE_MIN
  const share = Math.min(Math.max((score - SCORE_MIN) / (SCORE_MAX - SCORE_MIN), 0), 1)

  return { width: `${Math.round(share * 100)}%` }
})

const classTone = computed(() => {
  switch (props.preview?.riskClass) {
    case RiskClassEnum.A:
    case RiskClassEnum.B:
      return 'text-green-600 dark:text-green-400'
    case RiskClassEnum.C:
      return 'text-amber-600 dark:text-amber-400'
    default:
      return 'text-red-600 dark:text-red-400'
  }
})

// Риск словами: «Риск низкий», а не «A · 785»; балл — по наведению
const riskWord = computed(() => (props.preview ? t(`application.explanation.risk.${props.preview.riskClass}`) : ''))
const scoreTitle = computed(() =>
  props.preview
    ? t('sandbox.builder.preview.scoreTitle', { score: Math.round(animatedScore.value ?? props.preview.score), class: props.preview.riskClass })
    : '',
)

const pathText = computed(() => props.preview?.pathMeans.replace(LAW_REFERENCE_PATTERN, '') ?? '')
const isRepresentativeBlocked = computed(() => props.hasRepresentative && props.preview?.signMode === JOINT_SIGNING)

const barTone = computed(() => {
  switch (props.preview?.riskClass) {
    case RiskClassEnum.A:
    case RiskClassEnum.B:
      return 'bg-green-500'
    case RiskClassEnum.C:
      return 'bg-amber-500'
    default:
      return 'bg-red-500'
  }
})

function handleHighlight(fields: string[]) {
  emit('highlight', fields)
}

function handleBlockersHighlight() {
  emit('highlight', props.preview?.blockers.flatMap((blocker) => blocker.fields) ?? [])
}

function handleScoreHighlight() {
  emit('highlight', props.preview?.scoreFields ?? [])
}

function handleClearHighlight() {
  emit('highlight', [])
}

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <aside
    class="flex min-w-0 flex-col gap-4"
    :aria-busy="isLoading"
    :aria-label="t('sandbox.builder.preview.title')"
  >
    <SandboxPersonaPreviewSkeleton v-if="!preview && !hasError" />

    <AppErrorState
      v-else-if="!preview"
      :message="t('sandbox.builder.preview.loadError')"
      @retry="handleRetry"
    />

    <template v-else>
      <!-- Компания -->
      <div class="card-key p-5">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
              {{ t('sandbox.builder.preview.title') }}
            </p>

            <h2 class="mt-1 break-words text-lg font-bold tracking-tight text-fino-text">
              {{ preview.companyName }}
            </h2>
          </div>

          <span
            v-if="isLoading"
            class="mt-1 size-2 shrink-0 rounded-full bg-primary motion-safe:animate-pulse"
            :title="t('sandbox.builder.preview.updating')"
            aria-hidden="true"
          />
        </div>

        <p class="mt-2 line-clamp-3 text-sm leading-relaxed text-fino-text-muted">
          {{ preview.about }}
        </p>
      </div>

      <!-- Стоп для всей компании -->
      <div
        v-if="preview.blockers.length"
        class="rounded-3xl border border-red-500/30 bg-red-500/5 p-4"
        tabindex="0"
        @mouseenter="handleBlockersHighlight"
        @mouseleave="handleClearHighlight"
        @focus="handleBlockersHighlight"
        @blur="handleClearHighlight"
      >
        <p class="flex items-center gap-2 text-sm font-bold text-red-700 dark:text-red-400">
          <i
            class="pi pi-ban"
            aria-hidden="true"
          />
          {{ t('sandbox.builder.preview.stopTitle') }}
        </p>

        <ul class="mt-2 flex flex-col gap-1 text-sm text-fino-text">
          <li
            v-for="blocker in preview.blockers"
            :key="blocker.code"
          >
            {{ blocker.text }}
          </li>
        </ul>
      </div>

      <!-- Продукты: строки переезжают между состояниями -->
      <div class="card-key p-5">
        <h3 class="text-sm font-bold text-fino-text">
          {{ t('sandbox.builder.preview.products') }}
        </h3>

        <TransitionGroup
          tag="ul"
          class="mt-3 flex flex-col gap-2"
          move-class="transition-transform duration-300 ease-out motion-reduce:transition-none"
          enter-active-class="transition duration-200 motion-reduce:transition-none"
          enter-from-class="opacity-0"
        >
          <li
            v-for="product in preview.products"
            :key="product.code"
          >
            <SandboxPersonaPreviewProduct
              :product="product"
              :is-stopped="isStopped"
              @highlight="handleHighlight"
            />
          </li>
        </TransitionGroup>
      </div>

      <!-- Класс риска -->
      <div
        class="flex items-center gap-5 card-key p-5"
        tabindex="0"
        @mouseenter="handleScoreHighlight"
        @mouseleave="handleClearHighlight"
        @focus="handleScoreHighlight"
        @blur="handleClearHighlight"
      >
        <div class="min-w-0 flex-1">
          <p class="text-xs text-fino-text-muted">
            {{ t('sandbox.builder.preview.risk') }}
          </p>

          <p
            class="mt-0.5 text-2xl font-display font-black transition-colors duration-300 first-letter:uppercase
                   motion-reduce:transition-none"
            :class="classTone"
            :title="scoreTitle"
          >
            {{ riskWord }}
          </p>

          <div
            class="mt-2 h-2 overflow-hidden rounded-full bg-fino-surface-secondary"
            aria-hidden="true"
          >
            <div
              class="h-full rounded-full transition-all duration-500 motion-reduce:transition-none"
              :class="barTone"
              :style="scoreWidth"
            />
          </div>
        </div>
      </div>

      <!-- Кто подписывает и люди -->
      <div class="card-key p-5">
        <p
          class="flex items-start gap-2 text-sm leading-relaxed text-fino-text-muted"
          :title="preview.pathMeans"
        >
          <i
            class="pi pi-file-edit mt-0.5 shrink-0 text-primary"
            aria-hidden="true"
          />
          {{ pathText }}
        </p>

        <!-- Последствие устройства: при совместной подписи доверенность одного директора не работает -->
        <p
          v-if="isRepresentativeBlocked"
          class="mt-3 flex items-start gap-2 rounded-2xl bg-fino-amber-soft p-3 text-sm text-fino-text"
          :title="t('sandbox.builder.preview.representativeLaw')"
        >
          <i
            class="pi pi-info-circle mt-0.5 shrink-0 text-amber-700 dark:text-amber-400"
            aria-hidden="true"
          />
          {{ t('sandbox.builder.preview.representativeBlocked') }}
        </p>

        <ul class="mt-4 flex flex-wrap gap-2">
          <li
            v-for="person in preview.people"
            :key="person.fullName"
            class="rounded-full bg-fino-surface-secondary px-3 py-1 text-xs text-fino-text"
            :title="person.roleTitle"
          >
            <span class="font-semibold">{{ person.fullName }}</span>
            <span class="text-fino-text-muted"> · {{ person.badge }}</span>
          </li>
        </ul>
      </div>
    </template>
  </aside>
</template>
