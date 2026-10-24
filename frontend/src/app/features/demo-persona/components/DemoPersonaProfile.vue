<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import DemoPersonaProfileSkeleton from './DemoPersonaProfileSkeleton.vue'
import { useDemoPersona } from '@/app/composables/useDemoPersona'
import { useSession } from '@/app/composables/useSession'

defineProps<{
  // Кто человек в этой компании: «ИП», «Директор», «Сотрудник»; у сотрудника банка — его роль в банке
  caption: string
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const { demoPersona, isLoading, resetDemoPersona } = useDemoPersona()
const { logout: endSession } = useSession()

// Сменить пользователя = выйти и выбрать другого на экране входа: токен забывается, данные персоны сбрасываются
async function switchUser() {
  await endSession()
  resetDemoPersona()
  await router.push({ name: 'login' })
}
</script>

<template>
  <div class="flex min-w-0 items-center gap-1.5 sm:gap-2">
    <div
      v-if="demoPersona"
      class="flex min-w-0 items-center gap-3 sm:border-l-2 sm:border-fino-line sm:pl-3"
    >
      <div
        class="flex size-10 shrink-0 items-center justify-center rounded-full border-2 border-fino-line
               bg-fino-lime font-display text-sm font-black text-[#111]"
        :title="demoPersona.fullName"
        aria-hidden="true"
      >
        {{ demoPersona.initials }}
      </div>

      <div class="sr-only min-w-0 flex-col md:not-sr-only md:flex">
        <span class="max-w-56 truncate text-sm font-semibold text-fino-text">
          {{ demoPersona.fullName }}
        </span>

        <span class="max-w-56 truncate text-xs text-fino-text-muted">
          {{ caption }}
        </span>
      </div>
    </div>

    <DemoPersonaProfileSkeleton v-else-if="isLoading" />

    <button
      type="button"
      class="flex h-10 min-w-10 shrink-0 cursor-pointer items-center justify-center gap-2
             rounded-xl bg-fino-surface text-fino-text sm:px-3 btn-key
             focus-visible:outline-2 focus-visible:outline-primary"
      :aria-label="t('demoPersona.switchUser')"
      :title="t('demoPersona.switchUser')"
      @click="switchUser"
    >
      <i
        class="pi pi-users"
        aria-hidden="true"
      />

      <span class="hidden text-sm font-semibold sm:inline">{{ t('demoPersona.switchShort') }}</span>
    </button>
  </div>
</template>
