<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { RouteLocationRaw } from 'vue-router'

defineProps<{
  navigation: {
    name: string
    to: RouteLocationRaw
    icon: string
    label: string
    exact: boolean
  }[]
}>()

const { t } = useI18n({ useScope: 'global' })

function isItemActive(exact: boolean, isActive: boolean, isExactActive: boolean): boolean {
  return exact ? isExactActive : isActive
}
</script>

<template>
  <aside
    class="hidden w-72 shrink-0 self-start rounded-3xl lg:sticky lg:top-28
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
        :key="item.name"
        v-slot="{ href, navigate, isActive, isExactActive }"
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
            isItemActive(item.exact, isActive, isExactActive)
              ? 'bg-fino-accent font-semibold text-primary'
              : 'text-fino-text-muted hover:bg-fino-surface-hover hover:text-fino-text'
          "
          :aria-current="isItemActive(item.exact, isActive, isExactActive) ? 'page' : undefined"
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
  </aside>
</template>