<script setup lang="ts">
import Toast from 'primevue/toast'
import SandboxReviewerPanel from '@/app/features/sandbox/components/SandboxReviewerPanel.vue'

// Уведомления снизу справа, над кнопкой «Как проверить»: шапку и профиль не закрывают
const TOAST_STYLE = { bottom: '5rem' }
// На телефоне — во всю ширину и выше нижнего меню кабинета
const TOAST_BREAKPOINTS = { '1023px': { width: 'calc(100vw - 2rem)', right: '1rem', bottom: '9.5rem' } }
</script>

<template>
  <Toast
    position="bottom-right"
    :style="TOAST_STYLE"
    :breakpoints="TOAST_BREAKPOINTS"
  />
  <RouterView />
  <SandboxReviewerPanel />
</template>
