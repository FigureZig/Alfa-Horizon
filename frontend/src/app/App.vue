<script setup lang="ts">
import { watchEffect } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Toast from 'primevue/toast'
import SandboxReviewerPanel from '@/app/features/sandbox/components/SandboxReviewerPanel.vue'

const BRAND = 'Fino'

const { t } = useI18n({ useScope: 'global' })
const route = useRoute()

// Заголовок вкладки по странице: «Заявки · Fino» — вкладки и история браузера различимы; меняется вместе с языком
watchEffect(() => {
  const titleKey = route.meta.title

  document.title = typeof titleKey === 'string' ? `${t(titleKey)} · ${BRAND}` : BRAND
})

// Уведомления сверху справа, под шапкой: низ экрана занят плашкой сценария и кнопкой «Как проверить»
const TOAST_STYLE = { top: '6.5rem' }
// На телефоне — во всю ширину
const TOAST_BREAKPOINTS = { '1023px': { width: 'calc(100vw - 2rem)', right: '1rem', top: '6rem' } }
</script>

<template>
  <Toast
    position="top-right"
    :style="TOAST_STYLE"
    :breakpoints="TOAST_BREAKPOINTS"
  />
  <RouterView />
  <SandboxReviewerPanel />
</template>
