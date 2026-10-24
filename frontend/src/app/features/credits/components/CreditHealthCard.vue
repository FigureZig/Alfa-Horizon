<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CreditHealthCardSkeleton from './CreditHealthCardSkeleton.vue'
import CreditScoreGauge from './CreditScoreGauge.vue'
import type { CreditScoreInterface } from '@/app/types/company/credit-score-interface'
import type { Nullable } from '@/app/types/nullable'

// Клиенту — только балл на спидометре и риск словами; из чего складывается балл, видит специалист банка в досье
const props = defineProps<{
  creditScore: Nullable<CreditScoreInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })

const isSkeletonVisible = computed(() => props.isLoading && !props.creditScore)

// Одной строкой словами: «Банк оценивает риск компании как умеренный»
const summaryLine = computed(() => {
  const score = props.creditScore

  if (!score) return t('credits.score.description')

  const risk = t(`application.explanation.risk.${score.riskClass}`)

  return score.hasMissingFactors && !score.bkiKnown
    ? t('credits.score.summaryNoBki', { risk })
    : t('credits.score.summary', { risk })
})

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <section
    class="flex min-w-0 flex-col gap-4 card-key p-5"
    :aria-label="t('credits.score.title')"
  >
    <div>
      <h2 class="text-lg font-extrabold text-fino-text">
        {{ t('credits.score.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ summaryLine }}
      </p>
    </div>

    <CreditHealthCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('credits.score.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <template v-else-if="creditScore">
      <CreditScoreGauge
        :score="creditScore.score"
        :risk-class="creditScore.riskClass"
        :classes="creditScore.classes"
      />

      <p
        v-if="creditScore.hasMissingFactors"
        class="flex items-start gap-2 rounded-2xl border-2 border-fino-line bg-fino-violet-soft p-3 text-xs text-fino-text"
      >
        <i
          class="pi pi-info-circle mt-0.5"
          aria-hidden="true"
        />
        {{ creditScore.bkiKnown ? t('credits.score.missingFactors') : t('credits.score.noBki') }}
      </p>

      <p class="text-xs leading-relaxed text-fino-text-muted">
        {{ t('credits.score.clientNote') }}
      </p>
    </template>
  </section>
</template>
