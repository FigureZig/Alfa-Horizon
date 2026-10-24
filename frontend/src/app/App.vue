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
