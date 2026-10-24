<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import Menu from 'primevue/menu'
import type { SandboxPersonaGroupInterface } from '@/app/types/sandbox/sandbox-persona-group-interface'
import type { Nullable } from '@/app/types/nullable'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

// Буквы для значка компании: без формы и кавычек — «Вектор-Трейд» → «ВТ»
// Значок компании — в одном из акцентов макета: плитки различаются с первого взгляда
const MONOGRAM_COLORS = [
  'bg-fino-lime text-[#111]',
  'bg-fino-violet text-white',
  'bg-fino-blue text-white',
  'bg-fino-amber text-[#111]',
]
const LEGAL_FORM_PATTERN = /^(ООО|АО|ПАО|ИП)\s+/i
const QUOTES_PATTERN = /[«»"]/g

const props = defineProps<{
  group: SandboxPersonaGroupInterface
  isBusy: boolean
  // Кем входили в прошлый раз — подсвечиваем, чтобы смена роли не начиналась с поиска
  lastPersonaId: Nullable<string>
}>()

const emit = defineEmits<{
  login: [persona: SandboxPersonaInterface]
  edit: [group: SandboxPersonaGroupInterface]
  delete: [group: SandboxPersonaGroupInterface]
}>()

const { t } = useI18n({ useScope: 'global' })

const menu = useTemplateRef<InstanceType<typeof Menu>>('menu')
const menuId = `company-menu-${props.group.key}`

const title = computed(() => (props.group.isBank ? t('login.bankTile.title') : props.group.title ?? ''))

// Что за бизнес — одной строкой главного человека компании
const about = computed(() =>
  props.group.isBank ? t('login.bankTile.about') : props.group.personas[0]?.about ?? '',
)

const monogram = computed(() => {
  const words = title.value.replace(LEGAL_FORM_PATTERN, '').replace(QUOTES_PATTERN, '').split(/[\s-]+/).filter(Boolean)

  return words.slice(0, 2).map((word) => word[0]).join('').toUpperCase()
})

// Цвет — по ИНН, чтобы у компании он не менялся между заходами
const monogramClass = computed(() => {
  if (props.group.isBank) return 'bg-primary text-primary-contrast'

  const seed = [...props.group.key].reduce((sum, char) => sum + char.charCodeAt(0), 0)

  return MONOGRAM_COLORS[seed % MONOGRAM_COLORS.length]
})

const menuItems = computed(() => [
  { label: t('login.group.edit'), icon: 'pi pi-pencil', command: handleEdit },
  { label: t('login.group.delete'), icon: 'pi pi-trash', command: handleDelete },
])

function toggleMenu(event: Event) {
  menu.value?.toggle(event)
}

function handleLogin(persona: SandboxPersonaInterface) {
  emit('login', persona)
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
    class="flex h-full min-w-0 flex-col gap-4 card-key p-5"
    :aria-label="title"
  >
    <div class="flex items-start gap-3">
      <span
        class="flex size-11 shrink-0 -rotate-3 items-center justify-center rounded-2xl border-2 border-fino-line
               font-display text-sm font-black"
        :class="monogramClass"
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

    <!-- Кем войти: каждый человек — своя кнопка с ролью, ничего не спрятано в выпадающем списке -->
    <ul
      class="mt-auto flex flex-col gap-2"
      :aria-label="t('login.peopleLabel', { company: title })"
    >
      <li
        v-for="persona in group.personas"
        :key="persona.id"
      >
        <button
          type="button"
          class="group/person flex min-h-12 w-full cursor-pointer items-center gap-3 rounded-xl border-2 px-3 py-2
                 text-left transition-colors duration-200 hover:border-fino-line hover:bg-fino-lime-soft
                 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :class="persona.id === lastPersonaId ? 'border-fino-line bg-fino-lime-soft' : 'border-fino-border'"
          :disabled="isBusy"
          :aria-label="t('login.enterAs', { name: persona.fullName })"
          @click="handleLogin(persona)"
        >
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-semibold text-fino-text">{{ persona.fullName }}</span>
            <span class="block truncate text-xs text-fino-text-muted">
              {{ persona.badge }}<template v-if="persona.id === lastPersonaId"> · {{ t('login.lastLogin') }}</template>
            </span>
          </span>

          <i
            class="pi pi-arrow-right shrink-0 text-xs text-primary transition-transform duration-200
                   group-hover/person:translate-x-0.5 motion-reduce:transition-none"
            aria-hidden="true"
          />
        </button>
      </li>
    </ul>
  </article>
</template>
