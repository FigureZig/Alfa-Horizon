<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import AppSidebar from '@/app/components/layout/AppSidebar.vue'
import ApplicationPageSkeleton from '@/app/features/application/components/ApplicationPageSkeleton.vue'
import CompanyMenu from '@/app/features/demo-persona/components/CompanyMenu.vue'
import DemoPersonaProfile from '@/app/features/demo-persona/components/DemoPersonaProfile.vue'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { useDemoPersona } from '@/app/composables/useDemoPersona'

const props = defineProps<{
  inn: string
}>()

const BANK_ROUTE_PREFIX = 'bank-'
const VOTES_ROUTE_NAMES = ['votes', 'vote']

const { locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const { demoPersona, error: demoPersonaError, loadDemoPersona } = useDemoPersona()

const { me, isVotesOnly, error: accessError, loadAccess } = useCompanyAccess(() => props.inn)

// Создатель своей компании (id вида c12) может её менять
const ownerId = computed(() => (/^c\d+$/.test(demoPersona.value?.userId ?? '') ? demoPersona.value?.userId ?? null : null))

const isBankStaff = computed(() => demoPersona.value?.isBankStaff ?? false)
const isBankRoute = computed(() => String(route.name ?? '').startsWith(BANK_ROUTE_PREFIX))

// Страницы показываем, когда известна роль и маршрут ей подходит: клиент не видит рабочее место банка и наоборот.
// Если роль не загрузилась, страницы сами покажут свою ошибку.
const isVotesRoute = computed(() => VOTES_ROUTE_NAMES.includes(String(route.name ?? '')))
const isAccessKnown = computed(() => Boolean(me.value) || accessError.value)

// Клиент не видит рабочее место банка, а участник без доступа к счёту — ничего, кроме голосования
const isRoleMatching = computed(() =>
  isBankStaff.value === isBankRoute.value && isVotesOnly.value === isVotesRoute.value,
)

const isPageAllowed = computed(() =>
  demoPersonaError.value || (Boolean(demoPersona.value) && isAccessKnown.value && isRoleMatching.value),
)

function onDemoPersonaChange() {
  loadDemoPersona(props.inn)
  loadAccess()
}

function redirectByRole() {
  if (!demoPersona.value || !isAccessKnown.value) return

  const clientHome = isVotesOnly.value ? 'votes' : 'dashboard'

  if (isBankStaff.value && !isBankRoute.value) {
    router.replace({ name: 'bank-queue', params: { inn: props.inn } })
  } else if (!isBankStaff.value && isBankRoute.value) {
    router.replace({ name: clientHome, params: { inn: props.inn } })
  } else if (!isBankStaff.value && isVotesOnly.value !== isVotesRoute.value) {
    router.replace({ name: clientHome, params: { inn: props.inn } })
  }
}

watch([() => props.inn, locale], onDemoPersonaChange, { immediate: true })
watch([demoPersona, me, () => route.name], redirectByRole, { immediate: true })
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <div class="flex items-center gap-2">
          <CompanyMenu
            :inn="inn"
            :companies="me?.companies ?? []"
            :owner-id="ownerId"
          />
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
        :is-votes-only="isVotesOnly"
      />

      <main class="min-w-0 flex-1">
        <RouterView v-if="isPageAllowed" />

        <ApplicationPageSkeleton v-else />
      </main>
    </div>
  </div>
</template>
