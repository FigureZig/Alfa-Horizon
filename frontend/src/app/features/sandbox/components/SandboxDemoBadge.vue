<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div
    class="flex h-10 items-center gap-2 rounded-xl bg-orange-500/10
           px-2.5 text-orange-600 dark:text-orange-400 sm:px-3"
    role="status"
    :aria-label="t('sandbox.demoMode')"
  >
    <span class="relative flex size-5 items-center justify-center">
      <i
        class="pi pi-bolt"
        aria-hidden="true"
      />
      <span
        class="absolute -top-0.5 -right-0.5 size-2 rounded-full bg-orange-500
               motion-safe:animate-pulse"
        aria-hidden="true"
      />
    </span>

    <span class="hidden text-sm font-semibold sm:inline">
      {{ t('sandbox.demoMode') }}
    </span>
  </div>
</template>
