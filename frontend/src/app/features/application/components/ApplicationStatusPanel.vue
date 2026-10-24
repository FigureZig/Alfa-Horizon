<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ApplicationReasonInterface } from '@/app/types/application/application-interface'

// Главную причину отказа называет шапка заявки; здесь — остальные причины и подсказки банка
defineProps<{
  reasons: ApplicationReasonInterface[]
  hints: string[]
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <section class="flex flex-col gap-4">
    <ul
      v-if="reasons.length"
      class="flex flex-col gap-2"
    >
      <li
        v-for="reason in reasons"
        :key="reason.code"
        class="flex items-start gap-2 rounded-xl bg-fino-accent px-3 py-2 text-sm text-fino-text"
      >
        <i
          class="pi pi-exclamation-triangle mt-0.5 text-red-600 dark:text-red-400"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ reason.text }}</span>
      </li>
    </ul>

    <div v-if="hints.length">
      <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
        {{ t('application.statusPanel.hints') }}
      </p>

      <ul class="mt-2 flex flex-col gap-1.5">
        <li
          v-for="hint in hints"
          :key="hint"
          class="flex items-start gap-2 text-sm text-fino-text"
        >
          <i
            class="pi pi-lightbulb mt-0.5 text-primary"
            aria-hidden="true"
          />
          <span class="min-w-0 break-words">{{ hint }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
