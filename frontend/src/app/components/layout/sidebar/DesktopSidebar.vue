<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import SidebarAiCard from './SidebarAiCard.vue'

defineProps<{
  navigation: {
    to: string
    icon: string
    label: string
  }[]
}>()

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <aside
    class="hidden w-72 shrink-0 self-start rounded-3xl
           border border-fino-border bg-fino-surface
           p-4 shadow-sm motion-safe:animate-sidebar-enter
           lg:block"
  >
    <div class="mb-4 px-3 pt-2">
      <p
        class="text-xs font-semibold uppercase tracking-wider
               text-fino-text-muted"
      >
        {{ t('nav.menu') }}
      </p>
    </div>

    <nav class="flex flex-col gap-1">
      <RouterLink
        v-for="item in navigation"
        :key="item.to"
        v-slot="{ href, navigate, isActive }"
        :to="item.to"
        custom
      >
        <a
          :href="href"
          class="group flex items-center gap-3 rounded-2xl
                 px-4 py-3.5 text-sm font-medium
                 transition-all duration-200
                 hover:-translate-x-0.5
                 focus-visible:outline-2 focus-visible:outline-primary"
          :class="
            isActive
              ? 'bg-fino-accent font-semibold text-primary'
              : 'text-fino-text-muted hover:bg-fino-surface-hover hover:text-fino-text'
          "
          :aria-current="isActive ? 'page' : undefined"
          @click="navigate"
        >
          <i
            :class="item.icon"
            class="text-base"
            aria-hidden="true"
          />

          <span>{{ t(item.label) }}</span>

          <i
            class="pi pi-angle-right ml-auto text-xs opacity-40
                   transition-transform duration-200
                   group-hover:translate-x-0.5"
            aria-hidden="true"
          />
        </a>
      </RouterLink>
    </nav>

    <SidebarAiCard />
  </aside>
</template>