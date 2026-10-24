<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'

const props = defineProps<{
  forPercent: number
  againstPercent: number
  thresholdPercent: number
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatPercent } = useFormatters()

function clampPercent(percent: number): number {
  return Math.min(Math.max(percent, 0), 100)
}

// «За» растёт слева, «против» — справа; отметка порога стоит на месте
const forWidth = computed(() => ({ width: `${clampPercent(props.forPercent)}%` }))
const againstWidth = computed(() => ({ width: `${clampPercent(props.againstPercent)}%` }))
const thresholdPosition = computed(() => ({ left: `${clampPercent(props.thresholdPercent)}%` }))

const forText = computed(() => formatPercent(props.forPercent))
const againstText = computed(() => formatPercent(props.againstPercent))
const thresholdText = computed(() => formatPercent(props.thresholdPercent))
</script>

<template>
  <div>
    <div
      class="relative"
      role="img"
      :aria-label="t('application.approval.barLabel', { for: forText, against: againstText, threshold: thresholdText })"
    >
      <div class="flex h-2.5 justify-between overflow-hidden rounded-full bg-fino-surface-secondary">
        <div
          class="bg-green-500 transition-[width] duration-500 ease-out motion-reduce:transition-none"
          :style="forWidth"
        />
        <div
          class="bg-red-500 transition-[width] duration-500 ease-out motion-reduce:transition-none"
          :style="againstWidth"
        />
      </div>

      <span
        class="absolute -inset-y-1 w-0.5 -translate-x-1/2 rounded-full bg-fino-text"
        :style="thresholdPosition"
        aria-hidden="true"
      />
    </div>

    <p
      class="relative mt-2 flex justify-between text-xs text-fino-text-muted"
      aria-hidden="true"
    >
      <span>{{ t('application.approval.forPercent', { percent: forText }) }}</span>
      <span
        class="absolute -translate-x-1/2 font-semibold text-fino-text"
        :style="thresholdPosition"
      >{{ thresholdText }}</span>
      <span>{{ t('application.approval.againstPercent', { percent: againstText }) }}</span>
    </p>
  </div>
</template>
