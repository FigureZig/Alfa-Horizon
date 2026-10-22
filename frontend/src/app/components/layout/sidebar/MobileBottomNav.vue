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
  <nav
    class="fixed inset-x-0 bottom-0 z-50
           border-t border-fino-border bg-fino-surface
           px-2 pt-2 pb-[calc(env(safe-area-inset-bottom)+0.5rem)]
           shadow-[0_-4px_24px_rgba(0,0,0,0.05)]
           lg:hidden"
    :aria-label="t('nav.menu')"
  >
    <div class="mx-auto grid max-w-lg grid-cols-3 gap-1">
      <RouterLink
        v-for="item in navigation"
        :key="item.name"
        v-slot="{ href, navigate, isActive, isExactActive }"
        :to="item.to"
        custom
      >
        <a
          :href="href"
          class="flex min-w-0 flex-col items-center
                 justify-center gap-1 rounded-xl
                 px-1 py-1.5 text-center
                 transition-colors duration-200
                 focus-visible:outline-2
                 focus-visible:outline-primary"
          :class="
            isActive
              ? 'text-primary'
              : 'text-fino-text-muted hover:text-fino-text'
          "
          :aria-current="isItemActive(item.exact, isActive, isExactActive) ? 'page' : undefined"
          @click="navigate"
        >
          <span
            class="flex h-9 w-12 items-center justify-center
                   rounded-xl transition-colors duration-200"
            :class="
              isItemActive(item.exact, isActive, isExactActive) ? 'bg-fino-accent' : 'bg-transparent'
            "
          >
            <i
              :class="item.icon"
              class="text-lg"
              aria-hidden="true"
            />
          </span>

          <span
            class="w-full truncate text-[10px] leading-tight
                   sm:text-xs"
            :class="isItemActive(item.exact, isActive, isExactActive) ? 'font-semibold' : 'font-medium'"
          >
            {{ t(item.label) }}
          </span>
        </a>
      </RouterLink>
    </div>
  </nav>
</template>