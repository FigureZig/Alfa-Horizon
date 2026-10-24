<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import type { BankPercentilesInterface } from '@/app/types/bank/bank-metrics-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  title: string
  description: string
  timing: BankPercentilesInterface
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDuration, formatPercent } = useFormatters()

function formatSeconds(value: Nullable<number>): string {
  return value === null ? '—' : formatDuration(value)
}

const median = computed(() => formatSeconds(props.timing.medianSeconds))
const p95 = computed(() => formatSeconds(props.timing.p95Seconds))
const target = computed(() => formatSeconds(props.timing.targetSeconds))

// Доля замеров в пределах цели: ниже 100 % — повод присмотреться
const withinTarget = computed(() =>
  props.timing.withinTargetShare === null ? '—' : formatPercent(props.timing.withinTargetShare * 100),
)

const isWithinTarget = computed(() => props.timing.withinTargetShare === 1)
</script>

<template>
  <article class="flex min-w-0 flex-col gap-4 card-key p-5">
    <div>
      <h2 class="text-sm font-semibold text-fino-text">
        {{ title }}
      </h2>

      <p class="mt-1 text-xs text-fino-text-muted">
        {{ description }}
      </p>
    </div>

    <p
      v-if="!timing.count"
      class="text-sm text-fino-text-muted"
    >
      {{ t('bank.metrics.noData') }}
    </p>

    <template v-else>
      <dl class="grid grid-cols-2 gap-4">
        <div>
          <dt class="text-xs text-fino-text-muted">
            {{ t('bank.metrics.median') }}
          </dt>
          <dd class="mt-0.5 text-2xl font-display font-black text-fino-text">
            {{ median }}
          </dd>
        </div>

        <div>
          <dt class="text-xs text-fino-text-muted">
            {{ t('bank.metrics.p95') }}
          </dt>
          <dd class="mt-0.5 text-2xl font-display font-black text-fino-text">
            {{ p95 }}
          </dd>
        </div>
      </dl>

      <p
        class="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-xl p-3 text-xs"
        :class="isWithinTarget
          ? 'border-2 border-fino-line bg-fino-lime text-[#111]'
          : 'bg-fino-surface-secondary text-fino-text-muted'"
      >
        <i
          :class="isWithinTarget ? 'pi pi-check-circle' : 'pi pi-flag'"
          aria-hidden="true"
        />
        <span class="font-semibold">{{ t('bank.metrics.withinTarget', { share: withinTarget }) }}</span>
        <span>{{ t('bank.metrics.target', { target }) }}</span>
      </p>
    </template>
  </article>
</template>
