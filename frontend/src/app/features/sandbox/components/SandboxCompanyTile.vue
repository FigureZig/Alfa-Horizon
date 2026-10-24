<script setup lang="ts">
import { computed, ref, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import Menu from 'primevue/menu'
import Select from 'primevue/select'
import type { SandboxPersonaGroupInterface } from '@/app/types/sandbox/sandbox-persona-group-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

// Буквы для значка компании: без формы и кавычек — «Вектор-Трейд» → «ВТ»
const LEGAL_FORM_PATTERN = /^(ООО|АО|ПАО|ИП)\s+/i
const QUOTES_PATTERN = /[«»"]/g

const props = defineProps<{
  group: SandboxPersonaGroupInterface
  isBusy: boolean
}>()

const emit = defineEmits<{
  login: [persona: SandboxPersonaInterface]
  edit: [group: SandboxPersonaGroupInterface]
  delete: [group: SandboxPersonaGroupInterface]
}>()

const { t } = useI18n({ useScope: 'global' })

const menu = useTemplateRef<InstanceType<typeof Menu>>('menu')
const menuId = `company-menu-${props.group.key}`
const selectId = `company-people-${props.group.key}`

// Первым в компании идёт её главный человек — директор или ИП
const selectedId = ref(props.group.personas[0]?.id ?? '')

const title = computed(() => (props.group.isBank ? t('login.bankTile.title') : props.group.title ?? ''))

// Что за бизнес — одной строкой главного человека компании
const about = computed(() =>
  props.group.isBank ? t('login.bankTile.about') : props.group.personas[0]?.about ?? '',
)

const monogram = computed(() => {
  const words = title.value.replace(LEGAL_FORM_PATTERN, '').replace(QUOTES_PATTERN, '').split(/[\s-]+/).filter(Boolean)

  return words.slice(0, 2).map((word) => word[0]).join('').toUpperCase()
})

const selectedPersona = computed(() =>
  props.group.personas.find((persona) => persona.id === selectedId.value) ?? props.group.personas[0] ?? null,
)
const hasChoice = computed(() => props.group.personas.length > 1)

const menuItems = computed(() => [
  { label: t('login.group.edit'), icon: 'pi pi-pencil', command: handleEdit },
  { label: t('login.group.delete'), icon: 'pi pi-trash', command: handleDelete },
])

function toggleMenu(event: Event) {
  menu.value?.toggle(event)
}

function handleLogin() {
  if (selectedPersona.value) {
    emit('login', selectedPersona.value)
  }
}

function handleEdit() {
  emit('edit', props.group)
}

function handleDelete() {
  emit('delete', props.group)
}
</script>

<template>
  <article
    class="flex h-full min-w-0 flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm
           transition-[border-color,box-shadow] duration-300 hover:border-primary/40 hover:shadow-md
           motion-reduce:transition-none"
    :aria-label="title"
  >
    <div class="flex items-start gap-3">
      <span
        class="flex size-11 shrink-0 items-center justify-center rounded-2xl text-sm font-bold"
        :class="group.isBank ? 'bg-primary text-primary-contrast' : 'bg-fino-accent text-primary'"
        aria-hidden="true"
      >
        <i
          v-if="group.isBank"
          class="pi pi-building-columns"
        />
        <template v-else>{{ monogram }}</template>
      </span>

      <div class="min-w-0 flex-1">
        <h2 class="break-words text-base font-bold leading-snug tracking-tight text-fino-text">
          {{ title }}
        </h2>

        <!-- Полное описание — во всплывающей подсказке: в карточке оно обрезано -->
        <p
          class="mt-1 line-clamp-2 text-sm leading-relaxed text-fino-text-muted sm:line-clamp-3"
          :title="about"
        >
          {{ about }}
        </p>
      </div>

      <!-- Меню есть только у своей компании: готовые компании мира не меняются -->
      <template v-if="group.ownerId">
        <button
          type="button"
          class="-mt-1 -mr-1 flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-xl
                 text-fino-text-muted transition-colors duration-200 hover:bg-fino-surface-hover hover:text-fino-text
                 focus-visible:outline-2 focus-visible:outline-primary motion-reduce:transition-none"
          :aria-label="t('login.group.menu')"
          aria-haspopup="true"
          :aria-controls="menuId"
          :disabled="isBusy"
          @click="toggleMenu"
        >
          <i
            class="pi pi-ellipsis-h"
            aria-hidden="true"
          />
        </button>

        <Menu
          :id="menuId"
          ref="menu"
          :model="menuItems"
          popup
        />
      </template>
    </div>

    <!-- Кем войти: у каждого значок роли, чтобы было понятно, зачем им входить -->
    <div class="mt-auto flex flex-col gap-2">
      <label
        :for="selectId"
        class="sr-only text-xs font-semibold text-fino-text-muted sm:not-sr-only"
      >
        {{ t('login.enterAsLabel') }}
      </label>

      <div class="flex items-stretch gap-2">
        <Select
          v-if="hasChoice"
          v-model="selectedId"
          :input-id="selectId"
          :options="group.personas"
          option-label="fullName"
          option-value="id"
          :disabled="isBusy"
          class="min-w-0 flex-1"
        >
          <!-- Роль первой: «Директор · Павел Орлов» — роль видна, даже если имя не помещается -->
          <template #value>
            <span
              v-if="selectedPersona"
              class="flex min-w-0 items-baseline gap-1.5 text-sm"
            >
              <span class="shrink-0 font-semibold text-fino-text">{{ selectedPersona.badge }}</span>
              <span class="truncate text-fino-text-muted">{{ selectedPersona.fullName }}</span>
            </span>
          </template>

          <template #option="{ option }">
            <span class="flex min-w-0 flex-col">
              <span class="flex min-w-0 items-center gap-2">
                <span class="truncate font-semibold">{{ option.fullName }}</span>
                <span class="shrink-0 rounded-md bg-fino-surface-secondary px-1.5 py-0.5 text-[11px] font-semibold text-fino-text-muted">
                  {{ option.badge }}
                </span>
              </span>
              <span class="mt-0.5 max-w-72 truncate text-xs text-fino-text-muted">{{ option.roleTitle }}</span>
            </span>
          </template>
        </Select>

        <p
          v-else-if="selectedPersona"
          :id="selectId"
          class="flex min-h-11 min-w-0 flex-1 items-baseline gap-1.5 self-center rounded-xl bg-fino-surface-secondary
                 px-3 py-3 text-sm"
        >
          <span class="shrink-0 font-semibold text-fino-text">{{ selectedPersona.badge }}</span>
          <span class="truncate text-fino-text-muted">{{ selectedPersona.fullName }}</span>
        </p>

        <button
          type="button"
          class="inline-flex min-h-11 shrink-0 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary
                 px-4 text-sm font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90
                 active:scale-95 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :disabled="isBusy || !selectedPersona"
          :aria-label="selectedPersona ? t('login.enterAs', { name: selectedPersona.fullName }) : t('login.enter')"
          @click="handleLogin"
        >
          {{ t('login.enter') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </button>
      </div>
    </div>
  </article>
</template>
