<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useToast } from 'primevue/usetoast'
import Dialog from 'primevue/dialog'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import SandboxCompanyTile from '@/app/features/sandbox/components/SandboxCompanyTile.vue'
import SandboxPersonaCardSkeleton from '@/app/features/sandbox/components/SandboxPersonaCardSkeleton.vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { useSession } from '@/app/composables/useSession'
import { sandboxService } from '@/app/services/sandbox/sandbox.service'
import { SandboxMapper } from '@/app/mappers/sandbox.mapper'
import { SandboxPersonaKindEnum } from '@/app/types/sandbox/sandbox-persona-kind-enum'
import type { AppLocale } from '@/app/i18n'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaGroupInterface } from '@/app/types/sandbox/sandbox-persona-group-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

const PERSONA_SKELETON_COUNT = 7
// Сколько компаний видно сразу: остальные — по кнопке «Ещё N компаний»
const VISIBLE_COMPANIES = 6
// Создатель своей компании — id вида c12, её люди — c12-p1: удаляют и правят компанию через создателя
const OWNER_ID_PATTERN = /^c\d+$/

const { t, locale } = useI18n({ useScope: 'global' })
const router = useRouter()
const toast = useToast()
const $fetch = useApiFetch()
const { enterCabinet } = useSession()

const personas = ref<SandboxPersonaInterface[]>([])
const isLoading = ref(false)
const isLoggingIn = ref(false)
const isDeleting = ref(false)
const error = ref(false)
const groupToDelete = ref<Nullable<SandboxPersonaGroupInterface>>(null)
const isDeleteDialogVisible = ref(false)
const isAllCompaniesVisible = ref(false)

// Люди по компаниям: свои компании первыми, сотрудники банка — последней группой
const groups = computed<SandboxPersonaGroupInterface[]>(() => {
  const byKey = new Map<string, SandboxPersonaGroupInterface>()

  for (const persona of personas.value) {
    const isBank = persona.kind === SandboxPersonaKindEnum.Bank
    const key = isBank || !persona.companyInn ? 'bank' : persona.companyInn
    const group = byKey.get(key) ?? {
      key,
      title: isBank ? null : persona.companyName,
      isBank,
      ownerId: null,
      personas: [],
    }

    group.personas.push(persona)

    if (persona.isCustom && !isBank && OWNER_ID_PATTERN.test(persona.id)) {
      group.ownerId = persona.id
    }

    byKey.set(key, group)
  }

  return [...byKey.values()].sort((first, second) =>
    Number(first.isBank) - Number(second.isBank)
    || Number(Boolean(second.ownerId)) - Number(Boolean(first.ownerId)),
  )
})

// Плитка = компания: свои компании первыми, сотрудники банка — отдельной плиткой в конце
const companyGroups = computed(() => groups.value.filter((group) => !group.isBank))
const bankGroup = computed(() => groups.value.find((group) => group.isBank) ?? null)
const visibleCompanies = computed(() =>
  isAllCompaniesVisible.value ? companyGroups.value : companyGroups.value.slice(0, VISIBLE_COMPANIES),
)
const hiddenCount = computed(() => companyGroups.value.length - visibleCompanies.value.length)

const isEmpty = computed(() => !isLoading.value && !error.value && !personas.value.length)

const deleteText = computed(() =>
  t('login.deleteDialog.text', { name: groupToDelete.value?.title ?? '' }),
)

async function loadPersonas() {
  if (isLoading.value) return

  isLoading.value = true
  error.value = false

  try {
    const { data } = await sandboxService.fetchPersonas($fetch, locale.value as AppLocale)

    personas.value = data.data.map((persona) => SandboxMapper.toEntity(persona))
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

async function loginAsPersona(persona: SandboxPersonaInterface) {
  if (isLoggingIn.value) return

  isLoggingIn.value = true

  try {
    // Вход на бэкенде: токен пользователя, его права и сбор данных компании
    await enterCabinet(persona.id)
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

function showAllCompanies() {
  isAllCompaniesVisible.value = true
}

function editGroup(group: SandboxPersonaGroupInterface) {
  if (!group.ownerId) return

  router.push({ name: 'login-company-edit', params: { personaId: group.ownerId } })
}

function askDeleteGroup(group: SandboxPersonaGroupInterface) {
  groupToDelete.value = group
  isDeleteDialogVisible.value = true
}

function cancelDelete() {
  isDeleteDialogVisible.value = false
}

async function confirmDelete() {
  const ownerId = groupToDelete.value?.ownerId

  if (!ownerId || isDeleting.value) return

  isDeleting.value = true

  try {
    await sandboxService.deletePersona($fetch, ownerId)

    isDeleteDialogVisible.value = false

    toast.add({
      severity: 'success',
      summary: t('toast.success'),
      detail: t('login.deleteDialog.done'),
      life: 3000,
    })

    await loadPersonas()
  } catch (err: unknown) {
    console.error('Sandbox company deleting failed:', err)

    toast.add({
      severity: 'error',
      summary: t('toast.error'),
      detail: t('toast.sandboxDeleteError'),
      life: 4000,
    })
  } finally {
    isDeleting.value = false
  }
}

onMounted(loadPersonas)
watch(locale, loadPersonas)
</script>

<template>
  <div class="min-h-screen bg-fino-surface-secondary">
    <AppHeader>
      <template #profile />
    </AppHeader>

    <!-- Снизу место под кнопку «Как проверить»: последнюю плитку она не закрывает -->
    <main class="mx-auto flex max-w-[1600px] flex-col gap-6 px-4 pt-6 pb-24 sm:gap-8 sm:px-6 sm:pt-10">
      <div class="max-w-2xl motion-safe:animate-fade-up">
        <h1 class="text-3xl font-bold tracking-tight text-fino-text sm:text-4xl">
          {{ t('login.title') }}
        </h1>

        <p class="mt-3 text-sm leading-relaxed text-fino-text-muted sm:text-base">
          {{ t('login.description') }}
        </p>
      </div>

      <!-- Скелетоны при загрузке -->
      <div
        v-if="isLoading && !personas.length"
        class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        aria-busy="true"
      >
        <SandboxPersonaCardSkeleton
          v-for="index in PERSONA_SKELETON_COUNT"
          :key="index"
        />
      </div>

      <AppErrorState
        v-else-if="error"
        :message="t('login.loadError')"
        @retry="loadPersonas"
      />

      <div
        v-else
        class="flex flex-col gap-4"
      >
        <ul
          class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          :aria-label="t('login.listLabel')"
        >
          <!-- Своя компания — первой: главный способ попробовать кабинет на своём бизнесе -->
          <li>
            <RouterLink
              :to="{ name: 'login-company' }"
              class="group relative flex h-full flex-row items-center gap-4 overflow-hidden rounded-3xl bg-primary p-4
                     text-primary-contrast shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg
                     focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
                     motion-reduce:transition-none motion-reduce:hover:translate-y-0
                     sm:min-h-40 sm:flex-col sm:items-stretch sm:justify-between sm:p-5"
            >
              <div
                class="pointer-events-none absolute -top-16 -right-14 size-44 rounded-full bg-white/10"
                aria-hidden="true"
              />

              <div class="relative flex min-w-0 flex-1 items-start gap-3 sm:flex-none">
                <span class="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-white/15 text-lg">
                  <i
                    class="pi pi-plus"
                    aria-hidden="true"
                  />
                </span>

                <div class="min-w-0">
                  <p class="text-base font-bold tracking-tight">
                    {{ t('login.ownCompany.title') }}
                  </p>

                  <p class="mt-1 line-clamp-2 text-sm leading-relaxed opacity-90">
                    {{ t('login.ownCompany.text') }}
                  </p>
                </div>
              </div>

              <span
                class="relative inline-flex min-h-11 w-fit shrink-0 items-center justify-center gap-2 rounded-xl bg-white
                       px-3.5 text-sm font-semibold text-primary sm:px-4"
              >
                <span class="hidden sm:inline">{{ t('login.ownCompany.action') }}</span>
                <i
                  class="pi pi-arrow-right text-xs transition-transform duration-200 group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </span>
            </RouterLink>
          </li>

          <li
            v-for="group in visibleCompanies"
            :key="group.key"
          >
            <SandboxCompanyTile
              :group="group"
              :is-busy="isLoggingIn || isDeleting"
              @login="loginAsPersona"
              @edit="editGroup"
              @delete="askDeleteGroup"
            />
          </li>

          <li v-if="bankGroup">
            <SandboxCompanyTile
              :group="bankGroup"
              :is-busy="isLoggingIn || isDeleting"
              @login="loginAsPersona"
            />
          </li>
        </ul>

        <button
          v-if="hiddenCount"
          type="button"
          class="mx-auto inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-xl border border-fino-border
                 bg-fino-surface px-5 text-sm font-semibold text-fino-text transition-colors hover:bg-fino-surface-hover
                 focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
          @click="showAllCompanies"
        >
          {{ t('login.moreCompanies', hiddenCount) }}
          <i
            class="pi pi-chevron-down text-xs"
            aria-hidden="true"
          />
        </button>

        <p
          v-if="isEmpty"
          class="rounded-3xl border border-dashed border-fino-border bg-fino-surface px-6 py-12 text-center
                 text-sm text-fino-text-muted"
        >
          {{ t('login.empty') }}
        </p>
      </div>
    </main>

    <Dialog
      v-model:visible="isDeleteDialogVisible"
      modal
      :header="t('login.deleteDialog.title')"
      :style="{ width: '26rem', maxWidth: '92vw' }"
    >
      <p class="text-sm leading-relaxed text-fino-text-muted">
        {{ deleteText }}
      </p>

      <template #footer>
        <button
          type="button"
          class="cursor-pointer rounded-xl border border-fino-border px-4 py-2 text-sm font-semibold
                 text-fino-text transition-colors hover:bg-fino-surface-hover motion-reduce:transition-none"
          @click="cancelDelete"
        >
          {{ t('login.deleteDialog.cancel') }}
        </button>

        <button
          type="button"
          class="cursor-pointer rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-contrast
                 transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60
                 motion-reduce:transition-none"
          :disabled="isDeleting"
          @click="confirmDelete"
        >
          {{ t('login.deleteDialog.confirm') }}
        </button>
      </template>
    </Dialog>
  </div>
</template>
