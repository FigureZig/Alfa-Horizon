<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { recentTransactions } from '@/mocks/dashboard'

const { t, locale } = useI18n({ useScope: 'global' })

const transactions = computed(() =>
    recentTransactions.map((item) => ({
      ...item,
      formattedAmount: `${item.amount > 0 ? '+' : '−'}${Math.abs(item.amount).toLocaleString(locale.value)} ₽`,
      formattedDate: new Intl.DateTimeFormat(locale.value, {
        day: 'numeric',
        month: 'short',
      }).format(new Date(`${item.date}T12:00:00`)),
    })),
)
</script>

<template>
  <section
    class="rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm sm:p-6"
  >
    <h2 class="mb-5 text-lg font-bold text-fino-text">
      {{ t('dashboard.recentTransactions') }}
    </h2>

    <div class="divide-y divide-fino-border">
      <div
        v-for="transaction in transactions"
        :key="transaction.id"
        class="flex items-center justify-between gap-3 py-4"
      >
        <div class="flex min-w-0 items-center gap-3">
          <div
            class="flex size-10 shrink-0 items-center justify-center
                   rounded-xl bg-fino-surface-secondary text-fino-text"
          >
            <i
              :class="
                transaction.amount > 0
                  ? 'pi pi-arrow-down-left'
                  : 'pi pi-arrow-up-right'
              "
              aria-hidden="true"
            />
          </div>

          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-fino-text">
              {{ t(transaction.title) }}
            </p>

            <p class="mt-1 text-xs text-fino-text-muted">
              {{ transaction.formattedDate }}
            </p>
          </div>
        </div>

        <span
          class="shrink-0 text-sm font-semibold tabular-nums"
          :class="
            transaction.amount > 0
              ? 'text-primary'
              : 'text-fino-text'
          "
        >
          {{ transaction.formattedAmount }}
        </span>
      </div>
    </div>
  </section>
</template>