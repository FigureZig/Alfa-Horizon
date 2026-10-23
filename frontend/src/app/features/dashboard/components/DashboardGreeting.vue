<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

type DayPeriod = 'morning' | 'day' | 'evening' | 'night'

const NOW_UPDATE_INTERVAL = 60_000

const props = defineProps<{
  firstName: string
  today: string
  organizationName: string
}>()

const { t, locale } = useI18n({ useScope: 'global' })

const now = ref(new Date())
let nowTimer: ReturnType<typeof setInterval> | undefined

function getDayPeriod(hours: number): DayPeriod {
  if (hours >= 5 && hours < 12) return 'morning'
  if (hours >= 12 && hours < 17) return 'day'
  if (hours >= 17 && hours < 23) return 'evening'

  return 'night'
}

const greeting = computed(() =>
  t(`dashboard.greeting.${getDayPeriod(now.value.getHours())}`, { name: props.firstName }),
)

// Дата — по часам мира из API, а не по браузеру: мир может жить не в сегодняшнем дне
const worldDate = computed(() => {
  const [year, month, day] = props.today.split('-').map(Number)

  return new Date(year, month - 1, day)
})

const currentDate = computed(() => {
  const dayMonth = new Intl.DateTimeFormat(locale.value, { day: 'numeric', month: 'long' }).format(worldDate.value)

  return t('dashboard.currentDate', { dayMonth, year: worldDate.value.getFullYear() })
})

// Приветствие и дата обновляются, если страница открыта долго
function updateNow() {
  now.value = new Date()
}

onMounted(() => {
  nowTimer = setInterval(updateNow, NOW_UPDATE_INTERVAL)
})

onBeforeUnmount(() => {
  clearInterval(nowTimer)
})
</script>

<template>
  <div class="min-w-0">
    <h1 class="break-words text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
      {{ greeting }}
    </h1>

    <p class="mt-2 break-words text-base font-medium text-fino-text">
      {{ organizationName }}
    </p>

    <p class="mt-1 text-sm text-fino-text-muted">
      {{ currentDate }}
    </p>
  </div>
</template>
