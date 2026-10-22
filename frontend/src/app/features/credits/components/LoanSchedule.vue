<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { LoanCalcScheduleRowInterface } from '@/app/types/catalog/loan-calc-interface'

const COLLAPSED_ROWS = 6

const props = defineProps<{
  schedule: LoanCalcScheduleRowInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency } = useFormatters()

const isExpanded = ref(false)

const isCollapsible = computed(() => props.schedule.length > COLLAPSED_ROWS)

const rows = computed(() =>
  (isExpanded.value ? props.schedule : props.schedule.slice(0, COLLAPSED_ROWS)).map((row) => ({
    number: row.number,
    payment: formatCurrency(row.payment, 'RUB'),
    interest: formatCurrency(row.interest, 'RUB'),
    principal: formatCurrency(row.principal, 'RUB'),
    balance: formatCurrency(row.balance, 'RUB'),
  })),
)

function toggleSchedule() {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div>
    <table class="w-full table-fixed text-left text-xs sm:text-sm">
      <caption class="sr-only">
        {{ t('credits.schedule.title') }}
      </caption>

      <thead class="text-fino-text-muted">
        <tr class="border-b border-fino-border">
          <th
            scope="col"
            class="w-8 py-2 pr-2 font-medium"
          >
            №
          </th>
          <th
            scope="col"
            class="py-2 pr-2 font-medium"
          >
            {{ t('credits.schedule.payment') }}
          </th>
          <th
            scope="col"
            class="py-2 pr-2 font-medium"
          >
            {{ t('credits.schedule.interest') }}
          </th>
          <th
            scope="col"
            class="hidden py-2 pr-2 font-medium sm:table-cell"
          >
            {{ t('credits.schedule.principal') }}
          </th>
          <th
            scope="col"
            class="py-2 text-right font-medium"
          >
            {{ t('credits.schedule.balance') }}
          </th>
        </tr>
      </thead>

      <tbody>
        <tr
          v-for="row in rows"
          :key="row.number"
          class="border-b border-fino-border last:border-b-0"
        >
          <td class="py-2 pr-2 text-fino-text-muted">
            {{ row.number }}
          </td>
          <td class="break-words py-2 pr-2 font-semibold text-fino-text">
            {{ row.payment }}
          </td>
          <td class="break-words py-2 pr-2 text-fino-text">
            {{ row.interest }}
          </td>
          <td class="hidden break-words py-2 pr-2 text-fino-text sm:table-cell">
            {{ row.principal }}
          </td>
          <td class="break-words py-2 text-right text-fino-text">
            {{ row.balance }}
          </td>
        </tr>
      </tbody>
    </table>

    <button
      v-if="isCollapsible"
      type="button"
      class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80
             focus-visible:outline-2 focus-visible:outline-primary"
      :aria-expanded="isExpanded"
      @click="toggleSchedule"
    >
      {{ isExpanded ? t('credits.schedule.showLess') : t('credits.schedule.showAll', { count: schedule.length }) }}
    </button>
  </div>
</template>
