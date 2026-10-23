<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import { useI18n } from 'vue-i18n'
import Menu from 'primevue/menu'
import SandboxPersonaCard from './SandboxPersonaCard.vue'
import type { SandboxPersonaGroupInterface } from '@/app/types/sandbox/sandbox-persona-group-interface'
import type { SandboxPersonaInterface } from '@/app/types/sandbox/sandbox-persona-interface'

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
const menuId = `group-menu-${props.group.key}`

const title = computed(() => props.group.title ?? t('login.group.bank'))

const menuItems = computed(() => [
  {
    label: t('login.group.edit'),
    icon: 'pi pi-pencil',
    command: handleEdit,
  },
  {
    label: t('login.group.delete'),
    icon: 'pi pi-trash',
    command: handleDelete,
  },
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
  <section :aria-label="title">
    <div class="mb-4 flex items-center justify-between gap-3">
      <div class="flex min-w-0 items-baseline gap-3">
        <h2 class="min-w-0 break-words text-lg font-bold tracking-tight text-fino-text">
          {{ title }}
        </h2>

        <span class="shrink-0 text-sm text-fino-text-muted">
          {{ t('login.group.members', group.personas.length) }}
        </span>
      </div>

      <!-- Меню есть только у своей компании: готовые компании мира не меняются -->
      <template v-if="group.ownerId">
        <button
          type="button"
          class="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-xl
                 text-fino-text-muted transition-colors duration-200 hover:bg-fino-surface-hover
                 hover:text-fino-text focus-visible:outline-2 focus-visible:outline-primary
                 motion-reduce:transition-none"
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

    <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
      <SandboxPersonaCard
        v-for="persona in group.personas"
        :key="persona.id"
        :persona="persona"
        :is-busy="isBusy"
        @login="handleLogin"
      />
    </div>
  </section>
</template>
