<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Menu from 'primevue/menu'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { authService } from '@/app/services/auth/auth.service'
import type { CompanyAccessInterface } from '@/app/types/company/company-access-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  inn: string
  companies: CompanyAccessInterface[]
  // Id создателя своей компании: только он её меняет; у готовых компаний мира пункта нет
  ownerId: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()
const $fetch = useApiFetch()

const menu = useTemplateRef<InstanceType<typeof Menu>>('menu')

const current = computed(() => props.companies.find((company) => company.inn === props.inn) ?? null)

// Меню нужно, если компаний несколько или компанию можно изменить
const isVisible = computed(() => Boolean(current.value) && (props.companies.length > 1 || Boolean(props.ownerId)))

const items = computed(() => {
  const switches = props.companies.length > 1
    ? props.companies.map((company) => ({
      label: company.shortName,
      icon: company.inn === props.inn ? 'pi pi-check' : 'pi pi-building',
      command: () => switchCompany(company.inn),
    }))
    : []

  const edit = props.ownerId
    ? [{ label: t('companyMenu.edit'), icon: 'pi pi-pencil', command: editCompany }]
    : []

  return [...switches, ...(switches.length && edit.length ? [{ separator: true }] : []), ...edit]
})

async function switchCompany(inn: string) {
  if (inn === props.inn) return

  try {
    await authService.switchCompany($fetch, inn)
  } catch (err: unknown) {
    // Переключение в адресе всё равно работает: кабинет строится по ИНН
    console.error('Company switching failed:', err)
  }

  await router.push({ name: 'dashboard', params: { inn } })
}

function editCompany() {
  if (!props.ownerId) return

  router.push({ name: 'login-company-edit', params: { personaId: props.ownerId } })
}

function toggleMenu(event: Event) {
  menu.value?.toggle(event)
}
</script>

<template>
  <div v-if="isVisible">
    <button
      type="button"
      class="flex h-10 max-w-48 cursor-pointer items-center gap-2 rounded-xl bg-fino-surface-secondary px-2.5
             text-fino-text transition-all duration-200 hover:-translate-y-0.5 hover:bg-fino-surface-hover
             active:scale-95 focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none sm:px-3"
      aria-haspopup="true"
      aria-controls="company-menu"
      :aria-label="t('companyMenu.label')"
      @click="toggleMenu"
    >
      <i
        class="pi pi-building"
        aria-hidden="true"
      />

      <span class="hidden min-w-0 truncate text-sm font-semibold lg:inline">
        {{ current?.shortName }}
      </span>

      <i
        class="pi pi-chevron-down text-xs text-fino-text-muted"
        aria-hidden="true"
      />
    </button>

    <Menu
      id="company-menu"
      ref="menu"
      :model="items"
      popup
    />
  </div>
</template>
