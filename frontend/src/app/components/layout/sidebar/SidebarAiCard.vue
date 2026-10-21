<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="mt-8 rounded-2xl bg-fino-surface-secondary p-4">
    <div
      class="mb-3 flex size-10 items-center justify-center
             rounded-xl bg-fino-accent text-primary"
    >
      <i
        class="pi pi-sparkles"
        aria-hidden="true"
      />
    </div>

    <p class="text-sm font-semibold text-fino-text">
      Fino AI
    </p>

    <p class="mt-1 text-xs leading-relaxed text-fino-text-muted">
      {{ t('nav.aiDescription') }}
    </p>

    <RouterLink
      to="/assistant"
      class="mt-4 inline-flex items-center gap-2
             text-sm font-semibold text-primary
             transition-all duration-200 hover:gap-3"
    >
      {{ t('nav.openAssistant') }}

      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </RouterLink>
  </div>
</template>