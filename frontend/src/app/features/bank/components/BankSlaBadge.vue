<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  slaUntil: Nullable<string>
  flags: ApplicationFlagEnum[]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

const isBreached = computed(() => props.flags.includes(ApplicationFlagEnum.SlaBreach))

const label = computed(() => {
  if (isBreached.value) return t('bank.sla.breached')
  if (!props.slaUntil) return ''

  return t('bank.sla.until', { date: formatDateTime(props.slaUntil, { hour: '2-digit', minute: '2-digit' }) })
})
</script>

<template>
  <span
    v-if="label"
    class="inline-flex w-fit items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold"
    :class="isBreached
      ? 'bg-red-500/10 text-red-700 dark:text-red-400'
      : 'bg-fino-surface-secondary text-fino-text-muted'"
  >
    <i
      :class="isBreached ? 'pi pi-exclamation-triangle' : 'pi pi-clock'"
      class="text-xs"
      aria-hidden="true"
    />
    {{ label }}
  </span>
</template>
