<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
        {{ t('applications.title') }}
      </h1>

      <p class="mt-2 text-sm text-fino-text-muted">
        {{ t('applications.description') }}
      </p>
    </div>

    <!-- Раздел появится позже -->
    <div
      class="flex flex-col items-center rounded-3xl border border-dashed
             border-fino-border bg-fino-surface px-6 py-12 text-center"
    >
      <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-file-edit text-2xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 max-w-xs text-sm text-fino-text-muted">
        {{ t('common.comingSoon') }}
      </p>
    </div>
  </div>
</template>
