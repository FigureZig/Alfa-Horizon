<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import DemoPersonaProfileSkeleton from './DemoPersonaProfileSkeleton.vue'
import { useDemoPersona } from '@/app/composables/useDemoPersona'

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { demoPersona, isLoading, resetDemoPersona } = useDemoPersona()

// Завершаем только демо-сессию: основная авторизация (если появится) не затрагивается
function logout() {
  resetDemoPersona()
  router.push({ name: 'sandbox' })
}
</script>

<template>
  <div class="flex min-w-0 items-center gap-1.5 sm:gap-2">
    <div
      v-if="demoPersona"
      class="flex min-w-0 items-center gap-3 sm:border-l sm:border-fino-border sm:pl-3"
    >
      <div
        class="flex size-10 shrink-0 items-center justify-center rounded-full
               bg-fino-accent text-sm font-bold text-primary"
        :title="demoPersona.fullName"
        aria-hidden="true"
      >
        {{ demoPersona.initials }}
      </div>

      <div class="sr-only min-w-0 flex-col md:not-sr-only md:flex">
        <span class="max-w-48 truncate text-sm font-semibold text-fino-text">
          {{ demoPersona.fullName }}
        </span>

        <span class="text-xs text-fino-text-muted">
          {{ t('demoPersona.caption') }}
        </span>
      </div>
    </div>

    <DemoPersonaProfileSkeleton v-else-if="isLoading" />

    <button
      type="button"
      class="flex size-10 shrink-0 cursor-pointer items-center justify-center
             rounded-xl bg-fino-surface-secondary text-fino-text
             transition-all duration-200
             hover:-translate-y-0.5 hover:bg-fino-surface-hover hover:text-primary
             active:scale-95
             focus-visible:outline-2 focus-visible:outline-primary
             motion-reduce:transition-none motion-reduce:hover:translate-y-0"
      :aria-label="t('demoPersona.logout')"
      :title="t('demoPersona.logout')"
      @click="logout"
    >
      <i
        class="pi pi-sign-out"
        aria-hidden="true"
      />
    </button>
  </div>
</template>
