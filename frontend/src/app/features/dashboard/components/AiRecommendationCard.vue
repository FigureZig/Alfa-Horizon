<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <section
    class="flex flex-col justify-between gap-5 rounded-3xl
           border border-fino-border bg-fino-accent
           p-5 sm:p-6"
  >
    <div>
      <div
        class="mb-5 flex size-12 items-center justify-center
               rounded-2xl bg-fino-surface text-primary"
      >
        <i
          class="pi pi-sparkles text-xl"
          aria-hidden="true"
        />
      </div>

      <p class="text-sm font-semibold text-primary">
        Fino AI
      </p>

      <h2 class="mt-2 text-xl font-bold tracking-tight text-fino-text">
        {{ t('dashboard.aiTitle') }}
      </h2>

      <p class="mt-3 text-sm leading-relaxed text-fino-text-muted">
        {{ t('dashboard.aiDescription') }}
      </p>
    </div>

    <RouterLink
      to="/credits"
      class="inline-flex w-fit items-center justify-center gap-2
             rounded-xl bg-primary px-5 py-3 text-sm font-semibold
             text-primary-contrast transition-all duration-200
             hover:opacity-90 active:scale-95"
    >
      {{ t('dashboard.findCredit') }}
      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </RouterLink>
  </section>
</template>