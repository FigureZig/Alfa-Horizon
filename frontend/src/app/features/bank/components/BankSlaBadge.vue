<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type { Nullable } from '@/app/types/nullable'

const MS_IN_MINUTE = 60_000
const MINUTES_IN_HOUR = 60
// Цвет по остатку: больше двух часов — спокойно, меньше — пора, меньше часа — горит
const CALM_MINUTES = 120
const URGENT_MINUTES = 60

const NEUTRAL_CLASS = 'bg-fino-surface-secondary text-fino-text-muted'
const WARNING_CLASS = 'border-2 border-fino-line bg-fino-amber text-[#111]'
const DANGER_CLASS = 'border-2 border-fino-line bg-primary text-primary-contrast'

const props = defineProps<{
  slaUntil: Nullable<string>
  flags: ApplicationFlagEnum[]
  // «Сейчас» по часам мира, мс; без него показываем срок датой и временем
  now?: Nullable<number>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

const minutesLeft = computed(() => {
  if (!props.slaUntil || props.now === undefined || props.now === null) return null

  return Math.floor((new Date(props.slaUntil).getTime() - props.now) / MS_IN_MINUTE)
})

const isBreached = computed(() =>
  props.flags.includes(ApplicationFlagEnum.SlaBreach) || (minutesLeft.value !== null && minutesLeft.value <= 0),
)

// «Осталось 3 ч 40 мин», а не «Срок до 02:42»: отсчёт понятнее времени без даты
const label = computed(() => {
  if (isBreached.value) return t('bank.sla.breached')
  if (!props.slaUntil) return ''

  const minutes = minutesLeft.value

  if (minutes === null) {
    return t('bank.sla.until', {
      date: formatDateTime(props.slaUntil, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
    })
  }

  const hours = Math.floor(minutes / MINUTES_IN_HOUR)

  return hours
    ? t('bank.sla.hoursLeft', { hours, minutes: minutes % MINUTES_IN_HOUR })
    : t('bank.sla.minutesLeft', { minutes })
})

const toneClass = computed(() => {
  if (isBreached.value) return DANGER_CLASS
  if (minutesLeft.value === null || minutesLeft.value > CALM_MINUTES) return NEUTRAL_CLASS

  return minutesLeft.value > URGENT_MINUTES ? WARNING_CLASS : DANGER_CLASS
})
</script>

<template>
  <span
    v-if="label"
    class="inline-flex w-fit items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-semibold whitespace-nowrap"
    :class="toneClass"
  >
    <i
      :class="isBreached ? 'pi pi-exclamation-triangle' : 'pi pi-clock'"
      class="text-xs"
      aria-hidden="true"
    />
    {{ label }}
  </span>
</template>
