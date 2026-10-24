<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaPreviewInterface } from '@/app/types/sandbox/sandbox-persona-preview-interface'

const props = defineProps<{
  preview: Nullable<SandboxPersonaPreviewInterface>
  isLoading: boolean
}>()

const emit = defineEmits<{
  show: []
}>()

const { t } = useI18n({ useScope: 'global' })

const availableCount = computed(() => props.preview?.products.filter((product) => product.isAvailable).length ?? 0)
const totalCount = computed(() => props.preview?.products.length ?? 0)
const isStopped = computed(() => Boolean(props.preview?.blockers.length))

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

function handleShow() {
  emit('show')
}
</script>

<template>
  <!-- Мобильная полоса: предпросмотр уходит под форму, поэтому главное из него держим на виду -->
  <div
    v-if="preview"
    class="fixed inset-x-0 bottom-0 z-30 border-t border-fino-border bg-fino-surface/95 px-4 pt-3 backdrop-blur
           pb-[calc(0.75rem+env(safe-area-inset-bottom))] lg:hidden"
  >
    <button
      type="button"
      class="flex w-full cursor-pointer items-center gap-4 text-left focus-visible:outline-2 focus-visible:outline-primary"
      :aria-label="t('sandbox.builder.preview.title')"
      @click="handleShow"
    >
      <!-- Риск словами, а не буквой класса -->
      <span class="flex shrink-0 flex-col">
        <span class="text-[11px] text-fino-text-muted">{{ t('sandbox.builder.preview.risk') }}</span>
        <span
          class="text-base font-bold tracking-tight first-letter:uppercase"
          :class="classTone"
        >
          {{ t(`application.explanation.risk.${preview.riskClass}`) }}
        </span>
      </span>

      <span class="min-w-0 flex-1">
        <span class="block text-sm font-semibold text-fino-text">
          {{ isStopped ? t('sandbox.builder.preview.stopTitle') : t('sandbox.builder.preview.barAvailable', { available: availableCount, total: totalCount }) }}
        </span>
        <span class="block text-xs text-fino-text-muted">
          {{ isLoading ? t('sandbox.builder.preview.updating') : t('sandbox.builder.preview.barMore') }}
        </span>
      </span>

      <i
        class="pi pi-chevron-up text-sm text-fino-text-muted"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
