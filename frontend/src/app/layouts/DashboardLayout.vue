<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import AppSidebar from '@/app/components/layout/AppSidebar.vue'
import ApplicationPageSkeleton from '@/app/features/application/components/ApplicationPageSkeleton.vue'
import DemoPersonaProfile from '@/app/features/demo-persona/components/DemoPersonaProfile.vue'
import SandboxWorldPanel from '@/app/features/sandbox/components/SandboxWorldPanel.vue'
import { useDemoPersona } from '@/app/composables/useDemoPersona'

const props = defineProps<{
  inn: string
}>()

const BANK_ROUTE_PREFIX = 'bank-'

const { locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const { demoPersona, error: demoPersonaError, loadDemoPersona } = useDemoPersona()

const isBankStaff = computed(() => demoPersona.value?.isBankStaff ?? false)
const isBankRoute = computed(() => String(route.name ?? '').startsWith(BANK_ROUTE_PREFIX))

// Страницы показываем, когда известна роль и маршрут ей подходит: клиент не видит рабочее место банка и наоборот.
// Если роль не загрузилась, страницы сами покажут свою ошибку.
const isPageAllowed = computed(() =>
  demoPersonaError.value || (Boolean(demoPersona.value) && isBankStaff.value === isBankRoute.value),
)

function onDemoPersonaChange() {
  loadDemoPersona(props.inn)
}

function redirectByRole() {
  if (!demoPersona.value) return

  if (isBankStaff.value && !isBankRoute.value) {
    router.replace({ name: 'bank-queue', params: { inn: props.inn } })
  } else if (!isBankStaff.value && isBankRoute.value) {
    router.replace({ name: 'dashboard', params: { inn: props.inn } })
  }
}

watch([() => props.inn, locale], onDemoPersonaChange, { immediate: true })
watch([demoPersona, () => route.name], redirectByRole, { immediate: true })
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <div class="flex items-center gap-2">
          <SandboxWorldPanel :inn="isBankStaff ? undefined : inn" />
          <DemoPersonaProfile />
        </div>
      </template>
    </AppHeader>

    <div
      class="mx-auto flex max-w-[1600px] items-start
             gap-6 px-4 pt-6
             pb-[calc(7rem+env(safe-area-inset-bottom))]
             sm:px-6 lg:pb-6"
    >
      <AppSidebar
        :inn="inn"
        :is-bank-staff="isBankStaff"
      />

      <main class="min-w-0 flex-1">
        <RouterView v-if="isPageAllowed" />

        <ApplicationPageSkeleton v-else />
      </main>
    </div>
  </div>
</template>
