<script setup lang="ts">
import { computed } from 'vue'
import DesktopSidebar from './sidebar/DesktopSidebar.vue'
import MobileBottomNav from './sidebar/MobileBottomNav.vue'

const props = defineProps<{
  inn: string
  isBankStaff: boolean
}>()

// Главная — дочерний маршрут с пустым путём, поэтому активна только при точном совпадении.
const CLIENT_NAVIGATION = [
  { name: 'dashboard', icon: 'pi pi-home', label: 'nav.home', exact: true },
  { name: 'credits', icon: 'pi pi-wallet', label: 'nav.findCredit', exact: false },
  { name: 'applications', icon: 'pi pi-file-edit', label: 'nav.applications', exact: false },
]

// Рабочее место банка: очередь исключений (вместе с досье заявки) и метрики конвейера
const BANK_NAVIGATION = [
  { name: 'bank-queue', icon: 'pi pi-inbox', label: 'nav.queue', exact: false },
  { name: 'bank-metrics', icon: 'pi pi-chart-bar', label: 'nav.metrics', exact: false },
]

// ИНН демо-персоны передаётся в каждый пункт, чтобы разделы относились к текущему пользователю
const navigation = computed(() => (props.isBankStaff ? BANK_NAVIGATION : CLIENT_NAVIGATION).map((item) => ({
  ...item,
  to: { name: item.name, params: { inn: props.inn } },
})))
</script>

<template>
  <DesktopSidebar :navigation="navigation" />
  <MobileBottomNav :navigation="navigation" />
</template>
