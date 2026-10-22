<script setup lang="ts">
import { watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import AppSidebar from '@/app/components/layout/AppSidebar.vue'
import DemoPersonaProfile from '@/app/features/demo-persona/components/DemoPersonaProfile.vue'
import { useDemoPersona } from '@/app/composables/useDemoPersona'

const props = defineProps<{
  inn: string
}>()

const { locale } = useI18n({ useScope: 'global' })
const { loadDemoPersona } = useDemoPersona()

function onDemoPersonaChange() {
  loadDemoPersona(props.inn)
}

watch([() => props.inn, locale], onDemoPersonaChange, { immediate: true })
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <DemoPersonaProfile />
      </template>
    </AppHeader>

    <div
      class="mx-auto flex max-w-[1600px] items-start
             gap-6 px-4 pt-6
             pb-[calc(7rem+env(safe-area-inset-bottom))]
             sm:px-6 lg:pb-6"
    >
      <AppSidebar :inn="inn" />

      <main class="min-w-0 flex-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>
