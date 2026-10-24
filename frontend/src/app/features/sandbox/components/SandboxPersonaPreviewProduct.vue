<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAnimatedNumber } from '@/app/composables/useAnimatedNumber'
import { useFormatters } from '@/app/composables/useFormatters'
import type { SandboxPersonaPreviewProductInterface } from '@/app/types/sandbox/sandbox-persona-preview-interface'

const FLASH_DURATION = 1000

const props = defineProps<{
  product: SandboxPersonaPreviewProductInterface
  // У компании стоп-фактор: все продукты гаснут разом
  isStopped: boolean
}>()

const emit = defineEmits<{
  highlight: [fields: string[]]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent } = useFormatters()

const animatedMaxAmount = useAnimatedNumber(() => props.product.maxAmount)
const isFlashing = ref(false)

let flashTimer: ReturnType<typeof setTimeout> | undefined

const isDimmed = computed(() => props.isStopped || !props.product.isAvailable)

const reasons = computed(() => props.product.causes.map((cause) => cause.text).join('\n'))

const labelClass = computed(() => {
  if (props.isStopped || !props.product.isAvailable) return 'bg-fino-surface-secondary text-fino-text-muted'

  return props.product.rank === 0
    ? 'border-2 border-fino-line bg-fino-lime text-[#111]'
    : 'border-2 border-fino-line bg-fino-amber text-[#111]'
})

const stateLabel = computed(() =>
  props.isStopped ? t('sandbox.builder.preview.state.UNAVAILABLE') : t(`sandbox.builder.preview.state.${props.product.label}`),
)

function handleHighlight() {
  emit('highlight', props.product.causes.flatMap((cause) => cause.fields))
}

function handleClearHighlight() {
  emit('highlight', [])
}

// Одна мягкая подсветка изменившейся строки: состояние или максимум поменялись
watch(() => [props.product.label, props.product.maxAmount], () => {
  isFlashing.value = true
  clearTimeout(flashTimer)
  flashTimer = setTimeout(() => {
    isFlashing.value = false
  }, FLASH_DURATION)
})

onBeforeUnmount(() => clearTimeout(flashTimer))
</script>

<template>
  <button
    type="button"
    class="flex w-full min-w-0 cursor-pointer items-center gap-3 rounded-2xl px-4 py-3 text-left transition-all
           duration-300 hover:border-primary/40 focus-visible:outline-2 focus-visible:outline-primary
           motion-reduce:transition-none border-2 border-fino-line"
    :class="[isDimmed ? 'opacity-60' : '', isFlashing ? 'bg-fino-accent' : 'bg-fino-surface']"
    :title="isDimmed ? reasons : undefined"
    @mouseenter="handleHighlight"
    @mouseleave="handleClearHighlight"
    @focus="handleHighlight"
    @blur="handleClearHighlight"
  >
    <div class="min-w-0 flex-1">
      <p class="flex items-center gap-2 text-sm font-semibold text-fino-text">
        <span class="min-w-0 break-words">{{ product.name }}</span>

        <i
          v-if="product.isRecommended && !isStopped"
          class="pi pi-star-fill text-xs text-primary"
          :title="t('sandbox.builder.preview.recommended')"
          aria-hidden="true"
        />
      </p>

      <span
        class="mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold"
        :class="labelClass"
      >
        {{ stateLabel }}
      </span>
    </div>

    <div
      v-if="!isDimmed && animatedMaxAmount !== null"
      class="shrink-0 text-right"
    >
      <p class="text-sm font-bold whitespace-nowrap text-fino-text">
        {{ formatCurrency(animatedMaxAmount, 'RUB', true) }}
      </p>

      <p
        v-if="product.rate !== null"
        class="text-xs whitespace-nowrap text-fino-text-muted"
      >
        {{ formatPercent(product.rate) }}
      </p>
    </div>

    <i
      v-else
      class="pi pi-info-circle shrink-0 text-fino-text-muted"
      aria-hidden="true"
    />
  </button>
</template>
