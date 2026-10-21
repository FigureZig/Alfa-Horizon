<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { cashFlow } from '@/mocks/dashboard'

const { t, locale } = useI18n({ useScope: 'global' })

const maxValue = Math.max(
    ...cashFlow.flatMap((item) => [item.income, item.expenses]),
)

const months = computed(() =>
    cashFlow.map((item) => ({
      ...item,
      label: new Intl.DateTimeFormat(locale.value, {
        month: 'short',
      }).format(new Date(2026, item.month - 1, 1)),
      incomeHeight: `${(item.income / maxValue) * 100}%`,
      expensesHeight: `${(item.expenses / maxValue) * 100}%`,
    })),
)
</script>

<template>
  <section
    class="min-w-0 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm sm:p-6"
  >
    <div class="mb-6">
      <h2 class="text-lg font-bold text-fino-text">
        {{ t('dashboard.cashFlow') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ t('dashboard.lastSixMonths') }}
      </p>
    </div>

    <div class="mb-6 flex flex-wrap gap-4 text-xs text-fino-text-muted">
      <div class="flex items-center gap-2">
        <span class="size-3 rounded bg-primary" />
        {{ t('dashboard.income') }}
      </div>

      <div class="flex items-center gap-2">
        <span class="size-3 rounded bg-fino-accent-hover" />
        {{ t('dashboard.expenses') }}
      </div>
    </div>

    <div class="grid h-52 grid-cols-6 items-end gap-2 sm:gap-4">
      <div
        v-for="month in months"
        :key="month.month"
        class="flex h-full min-w-0 flex-col justify-end gap-2"
      >
        <div class="flex h-full items-end justify-center gap-1 sm:gap-2">
          <div
            class="w-3 max-w-6 flex-1 rounded-t-lg bg-primary
                   transition-all duration-300 sm:w-6"
            :style="{ height: month.incomeHeight }"
            :title="`${t('dashboard.income')}: ${month.income.toLocaleString(locale)} ₽`"
          />

          <div
            class="w-3 max-w-6 flex-1 rounded-t-lg bg-fino-accent-hover
                   transition-all duration-300 sm:w-6"
            :style="{ height: month.expensesHeight }"
            :title="`${t('dashboard.expenses')}: ${month.expenses.toLocaleString(locale)} ₽`"
          />
        </div>

        <span class="text-center text-[10px] text-fino-text-muted sm:text-xs">
          {{ month.label }}
        </span>
      </div>
    </div>
  </section>
</template>