<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'

defineProps<{
  flags: ApplicationFlagEnum[]
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <ul
    v-if="flags.length"
    class="flex flex-wrap gap-2"
  >
    <li
      v-for="flag in flags"
      :key="flag"
      class="inline-flex items-center gap-1.5 rounded-lg border border-fino-border px-2.5 py-1
             text-xs font-medium text-fino-text-muted"
    >
      <i
        class="pi pi-info-circle text-xs"
        aria-hidden="true"
      />
      {{ t(`application.flags.${flag}`) }}
    </li>
  </ul>
</template>
