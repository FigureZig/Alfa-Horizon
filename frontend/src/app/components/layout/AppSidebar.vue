<script setup lang="ts">
import DesktopSidebar from './sidebar/DesktopSidebar.vue'
import MobileBottomNav from './sidebar/MobileBottomNav.vue'

const navigation = [
  { to: '/', icon: 'pi pi-home', label: 'dashboard.title' },
  { to: '/credits', icon: 'pi pi-wallet', label: 'nav.credits' },
  { to: '/assistant', icon: 'pi pi-sparkles', label: 'nav.assistant' },
  { to: '/applications', icon: 'pi pi-file-edit', label: 'nav.applications' },
]
</script>

<template>
  <DesktopSidebar :navigation="navigation" />
  <MobileBottomNav :navigation="navigation" />
</template>