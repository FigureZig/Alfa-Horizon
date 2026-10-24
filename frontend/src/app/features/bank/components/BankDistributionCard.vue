<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

interface DistributionItemInterface {
  key: string
  label: string
  count: number
}

const props = defineProps<{
  title: string
  items: DistributionItemInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })

const total = computed(() => props.items.reduce((sum, item) => sum + item.count, 0))

const bars = computed(() =>
  [...props.items]
    .sort((a, b) => b.count - a.count)
    .map((item) => ({
      ...item,
      width: { width: `${total.value ? Math.max((item.count / total.value) * 100, 3) : 0}%` },
    })),
)
</script>

<template>
  <article class="flex min-w-0 flex-col gap-4 card-key p-5">
    <h2 class="text-sm font-semibold text-fino-text">
      {{ title }}
    </h2>

    <p
      v-if="!bars.length"
      class="text-sm text-fino-text-muted"
    >
      {{ t('bank.metrics.noData') }}
    </p>

    <ul
      v-else
      class="flex flex-col gap-3"
    >
      <li
        v-for="bar in bars"
        :key="bar.key"
      >
        <div class="flex items-baseline justify-between gap-3 text-sm">
          <span class="min-w-0 break-words text-fino-text">{{ bar.label }}</span>
          <span class="shrink-0 font-semibold text-fino-text">{{ bar.count }}</span>
        </div>

        <div class="mt-1.5 h-2 overflow-hidden rounded-full bg-fino-surface-secondary">
          <div
            class="h-full rounded-full bg-primary transition-all duration-500 motion-reduce:transition-none"
            :style="bar.width"
          />
        </div>
      </li>
    </ul>
  </article>
</template>
