<script setup lang="ts">
import { computed } from 'vue'
import DesktopSidebar from './sidebar/DesktopSidebar.vue'
import MobileBottomNav from './sidebar/MobileBottomNav.vue'

const props = defineProps<{
  inn: string
}>()

// ИНН демо-персоны передаётся в каждый пункт, чтобы разделы относились к текущему пользователю.
// Главная — дочерний маршрут с пустым путём, поэтому активна только при точном совпадении.
const navigation = computed(() => [
  { name: 'dashboard', icon: 'pi pi-home', label: 'nav.home', exact: true },
  { name: 'credits', icon: 'pi pi-wallet', label: 'nav.findCredit', exact: false },
  { name: 'applications', icon: 'pi pi-file-edit', label: 'nav.applications', exact: false },
].map((item) => ({
  ...item,
  to: { name: item.name, params: { inn: props.inn } },
})))
</script>

<template>
  <DesktopSidebar :navigation="navigation" />
  <MobileBottomNav :navigation="navigation" />
</template>
