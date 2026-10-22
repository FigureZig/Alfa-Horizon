<script setup lang="ts">
import { computed, nextTick, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import SandboxDemoBadge from '@/app/features/sandbox/components/SandboxDemoBadge.vue'
import SandboxPersonaCard from '@/app/features/sandbox/components/SandboxPersonaCard.vue'
import SandboxPersonaCardSkeleton from '@/app/features/sandbox/components/SandboxPersonaCardSkeleton.vue'
import SandboxPersonaDetails from '@/app/features/sandbox/components/SandboxPersonaDetails.vue'
import SandboxPersonaDetailsSkeleton from '@/app/features/sandbox/components/SandboxPersonaDetailsSkeleton.vue'
import SandboxWorldPanel from '@/app/features/sandbox/components/SandboxWorldPanel.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { AppLocale } from '@/app/i18n'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'
import type { Nullable } from '@/app/types/nullable'

const PERSONA_SKELETON_COUNT = 8

const { t, locale } = useI18n({ useScope: 'global' })
const route = useRoute()
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()

const personas = ref<SandboxPersonaInterface[]>([])
const selectedPersonaId = ref<Nullable<string>>(null)
const isLoading = ref(false)
const isLoggingIn = ref(false)
const { loginAsPersona: startSession } = useSession()
const error = ref(false)
const detailsRef = useTemplateRef<HTMLElement>('details')

const selectedPersona = computed(() =>
  personas.value.find((persona) => persona.id === selectedPersonaId.value) ?? null,
)

const officerPersona = computed(() =>
  personas.value.find((persona) => persona.kind === SandboxPersonaKindEnum.Bank) ?? null,
)

const isEmpty = computed(() => !isLoading.value && !error.value && !personas.value.length)

const guideCompanies = computed(() => {
  const companies = new Map<string, { inn: string, name: string, members: number }>()

  for (const persona of personas.value) {
    if (!persona.isCustom || persona.kind !== SandboxPersonaKindEnum.Client) continue

    const company = companies.get(persona.inn)
    if (company) {
      company.members++
    } else {
      companies.set(persona.inn, { inn: persona.inn, name: persona.organization, members: 1 })
    }
  }

  return [...companies.values()].filter((company) => company.members > 1)
})

async function loadPersonas() {
  if (isLoading.value) return

  isLoading.value = true
  error.value = false

  try {
    const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)

    personas.value = data.data
      .map((persona) => SandboxMapper.toEntity(persona))
      .sort((first, second) => Number(second.isCustom) - Number(first.isCustom))

    const requestedPersona = route.query.persona
    const requestedId = typeof requestedPersona === 'string' ? requestedPersona : null

    // После создания показываем владельца; при смене языка сохраняем текущий выбор.
    if (!selectedPersonaId.value && requestedId && personas.value.some((persona) => persona.id === requestedId)) {
      selectedPersonaId.value = requestedId
    }
    if (!selectedPersona.value) {
      selectedPersonaId.value = personas.value[0]?.id ?? null
    }
  } catch (err: unknown) {
    console.error('Sandbox personas loading failed:', err)
    error.value = true

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.sandboxLoadError'),
      life: 4000,
    })
  } finally {
    isLoading.value = false
  }
}

async function selectPersona(persona: SandboxPersonaInterface) {
  selectedPersonaId.value = persona.id

  // На узких экранах панель находится под карточками — прокручиваем к ней
  if (window.matchMedia('(min-width: 1280px)').matches) return

  await nextTick()

  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  detailsRef.value?.scrollIntoView({
    behavior: prefersReducedMotion ? 'auto' : 'smooth',
    block: 'start',
  })
}

async function loginAsPersona(persona: SandboxPersonaInterface) {
  if (isLoggingIn.value) return

  isLoggingIn.value = true

  try {
    // Вход на бэкенде: токен персоны, её права и сбор данных компании
    const signedInPersona = await startSession(persona.id)

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('sandbox.loginSuccess', { name: signedInPersona.fullName }),
      life: 4000,
    })

    // ИНН компании персоны в маршруте — по нему кабинет загружает все персональные данные;
    // сотрудник банка попадает сразу в очередь заявок
    const targetRoute = signedInPersona.kind === SandboxPersonaKindEnum.Bank ? 'bank-queue' : 'dashboard'

    await router.push({ name: targetRoute, params: { inn: signedInPersona.inn } })
  } catch (err: unknown) {
    console.error('Sandbox login failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.loginError'),
      life: 4000,
    })
  } finally {
    isLoggingIn.value = false
  }
}

function loginAsOfficer() {
  if (!officerPersona.value) return

  loginAsPersona(officerPersona.value)
}

function buildPersona() {
  router.push({ name: 'sandbox-persona-builder' })
}

onMounted(loadPersonas)
watch(locale, loadPersonas)
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile>
        <div class="flex items-center gap-2">
          <SandboxWorldPanel />
          <SandboxDemoBadge />
        </div>
      </template>
    </AppHeader>

    <main class="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 py-6 sm:px-6">
      <!-- Заголовок -->
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('sandbox.title') }}
        </h1>

        <p class="mt-2 max-w-2xl text-sm leading-relaxed text-fino-text-muted">
          {{ t('sandbox.description') }}
        </p>

        <RouterLink
          :to="{ name: 'sandbox-scenarios' }"
          class="mt-4 inline-flex min-h-11 items-center gap-2 rounded-xl border border-fino-border
                 bg-fino-surface px-4 py-2 text-sm font-semibold text-fino-text transition-colors
                 hover:border-primary focus-visible:outline-2 focus-visible:outline-primary
                 motion-reduce:transition-none"
        >
          <i
            class="pi pi-list-check text-primary"
            aria-hidden="true"
          />
          {{ t('sandbox.scenarios.open') }}
          <i
            class="pi pi-arrow-right text-xs text-primary"
            aria-hidden="true"
          />
        </RouterLink>
      </div>

      <section
        v-if="guideCompanies.length"
        class="rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-6"
        :aria-label="t('sandbox.guide.openGuide')"
      >
        <div class="flex items-start gap-3">
          <span class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary">
            <i
              class="pi pi-map"
              aria-hidden="true"
            />
          </span>
          <div>
            <h2 class="text-base font-bold text-fino-text">
              {{ t('sandbox.guide.openGuide') }}
            </h2>
            <p class="mt-1 text-sm text-fino-text-muted">
              {{ t('sandbox.guide.chooseCompany') }}
            </p>
          </div>
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <RouterLink
            v-for="company in guideCompanies"
            :key="company.inn"
            :to="{ name: 'sandbox-scenario-guide', params: { inn: company.inn } }"
            class="flex min-h-16 items-center justify-between gap-3 rounded-2xl border border-fino-border
                   bg-fino-surface-secondary px-4 py-3 transition-colors hover:border-primary"
          >
            <span class="min-w-0">
              <span class="block break-words text-sm font-semibold text-fino-text">{{ company.name }}</span>
              <span class="mt-1 block text-xs text-fino-text-muted">
                {{ t('sandbox.guide.memberCount', { count: company.members }) }}
              </span>
            </span>
            <i
              class="pi pi-arrow-right shrink-0 text-sm text-primary"
              aria-hidden="true"
            />
          </RouterLink>
        </div>
      </section>

      <!-- Скелетоны при загрузке -->
      <div
        v-if="isLoading"
        class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]"
        aria-busy="true"
      >
        <div class="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2">
          <SandboxPersonaCardSkeleton
            v-for="index in PERSONA_SKELETON_COUNT"
            :key="index"
          />
        </div>

        <SandboxPersonaDetailsSkeleton />
      </div>

      <!-- Ошибка загрузки -->
      <div
        v-else-if="error"
        class="rounded-3xl border border-fino-border bg-fino-surface p-6"
      >
        <div class="flex items-start gap-3">
          <i
            class="pi pi-exclamation-circle mt-0.5 text-xl text-primary"
            aria-hidden="true"
          />

          <div>
            <p class="text-sm font-medium text-fino-text">
              {{ t('sandbox.loadError') }}
            </p>

            <button
              type="button"
              class="mt-3 cursor-pointer text-sm font-semibold text-primary transition-opacity hover:opacity-80"
              @click="loadPersonas"
            >
              <i
                class="pi pi-refresh mr-1"
                aria-hidden="true"
              />
              {{ t('sandbox.retry') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Пустое состояние -->
      <div
        v-else-if="isEmpty"
        class="flex flex-col items-center rounded-3xl border border-dashed
               border-fino-border bg-fino-surface px-6 py-12 text-center"
      >
        <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
          <i
            class="pi pi-users text-2xl"
            aria-hidden="true"
          />
        </div>

        <p class="mt-4 max-w-xs text-sm text-fino-text-muted">
          {{ t('sandbox.empty') }}
        </p>
      </div>

      <!-- Персоны и панель выбранной персоны -->
      <div
        v-else
        class="grid grid-cols-1 items-start gap-6 xl:grid-cols-[minmax(0,1fr)_26rem]"
      >
        <section
          class="grid min-w-0 grid-cols-1 gap-4 sm:grid-cols-2"
          :aria-label="t('sandbox.personasLabel')"
        >
          <SandboxPersonaCard
            v-for="persona in personas"
            :key="persona.id"
            :persona="persona"
            :is-selected="persona.id === selectedPersonaId"
            @select="selectPersona"
          />

          <!-- Собрать свою персону -->
          <button
            type="button"
            class="group flex min-h-40 w-full cursor-pointer flex-col items-center
                   justify-center gap-3 rounded-3xl border border-dashed border-fino-border
                   bg-fino-surface p-5 text-center transition-all duration-200
                   hover:border-primary hover:bg-fino-accent
                   focus-visible:outline-2 focus-visible:outline-primary
                   motion-reduce:transition-none"
            @click="buildPersona"
          >
            <span
              class="flex size-12 items-center justify-center rounded-full
                     bg-fino-accent text-primary transition-colors
                     group-hover:bg-fino-surface"
            >
              <i
                class="pi pi-plus"
                aria-hidden="true"
              />
            </span>

            <span class="text-sm font-semibold text-fino-text">
              {{ t('sandbox.buildPersona') }}
            </span>
          </button>
        </section>

        <div
          ref="details"
          class="min-w-0 scroll-mt-28 xl:sticky xl:top-28"
          aria-live="polite"
        >
          <Transition
            mode="out-in"
            enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
            enter-from-class="translate-y-2 opacity-0"
            leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
            leave-to-class="opacity-0"
          >
            <SandboxPersonaDetails
              v-if="selectedPersona"
              :key="selectedPersona.id"
              :persona="selectedPersona"
              :is-logging-in="isLoggingIn"
              @login="loginAsPersona"
              @login-as-officer="loginAsOfficer"
            />
          </Transition>
        </div>
      </div>
    </main>
  </div>
</template>
