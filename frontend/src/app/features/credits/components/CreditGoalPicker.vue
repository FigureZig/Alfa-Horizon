<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { Nullable } from '@/app/types/nullable'

const GOALS = Object.values(CreditGoalEnum)

defineProps<{
  goal: Nullable<CreditGoalEnum>
  amount: Nullable<number>
  termMonths: Nullable<number>
}>()

const emit = defineEmits<{
  'update:goal': [goal: Nullable<CreditGoalEnum>]
  'update:amount': [amount: Nullable<number>]
  'update:termMonths': [termMonths: Nullable<number>]
}>()

const { t, locale } = useI18n({ useScope: 'global' })

// Повторный выбор той же цели снимает её: подбор снова общий
function handleSelectGoal(goal: CreditGoalEnum, current: Nullable<CreditGoalEnum>) {
  emit('update:goal', goal === current ? null : goal)
}

function handleAmountChange(amount: number | null) {
  emit('update:amount', amount)
}

function handleTermChange(termMonths: number | null) {
  emit('update:termMonths', termMonths)
}
</script>

<template>
  <section
    class="flex flex-col gap-5 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6"
    :aria-label="t('credits.goal.title')"
  >
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('credits.goal.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('credits.goal.description') }}
      </p>
    </div>

    <div
      class="flex flex-wrap gap-2"
      role="group"
      :aria-label="t('credits.goal.title')"
    >
      <button
        v-for="item in GOALS"
        :key="item"
        type="button"
        class="min-h-10 cursor-pointer rounded-xl border px-3.5 py-2 text-sm font-medium transition-colors duration-200
               focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
        :class="item === goal
          ? 'border-primary bg-fino-accent text-primary'
          : 'border-fino-border bg-fino-surface text-fino-text hover:bg-fino-surface-hover'"
        :aria-pressed="item === goal"
        @click="handleSelectGoal(item, goal)"
      >
        {{ t(`application.goal.${item}`) }}
      </button>
    </div>

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div class="flex min-w-0 flex-col gap-2">
        <label
          for="credits-amount"
          class="text-sm font-semibold text-fino-text"
        >
          {{ t('credits.goal.amount') }}
        </label>

        <InputNumber
          :model-value="amount"
          input-id="credits-amount"
          :min="1"
          :max-fraction-digits="0"
          suffix=" ₽"
          :locale="locale"
          :placeholder="t('credits.goal.optional')"
          fluid
          @update:model-value="handleAmountChange"
        />
      </div>

      <div class="flex min-w-0 flex-col gap-2">
        <label
          for="credits-term"
          class="text-sm font-semibold text-fino-text"
        >
          {{ t('credits.goal.term') }}
        </label>

        <InputNumber
          :model-value="termMonths"
          input-id="credits-term"
          :min="1"
          :max="120"
          :max-fraction-digits="0"
          :suffix="` ${t('credits.goal.months')}`"
          :locale="locale"
          :placeholder="t('credits.goal.optional')"
          fluid
          @update:model-value="handleTermChange"
        />
      </div>
    </div>
  </section>
</template>
