<script setup lang="ts">
import { useI18n } from 'vue-i18n'

// isInline — без собственной рамки, для ошибки внутри карточки
defineProps<{
  message: string
  isInline?: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <div
    :class="isInline ? '' : 'rounded-3xl border border-fino-border bg-fino-surface p-6'"
    role="alert"
  >
    <div class="flex items-start gap-3">
      <i
        class="pi pi-exclamation-circle mt-0.5 text-xl text-primary"
        aria-hidden="true"
      />

      <div class="min-w-0">
        <p class="break-words text-sm font-medium text-fino-text">
          {{ message }}
        </p>

        <button
          type="button"
          class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80"
          @click="handleRetry"
        >
          <i
            class="pi pi-refresh mr-1"
            aria-hidden="true"
          />
          {{ t('common.retry') }}
        </button>
      </div>
    </div>
  </div>
</template>
