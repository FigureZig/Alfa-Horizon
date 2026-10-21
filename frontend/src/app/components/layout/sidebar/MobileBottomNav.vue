<script setup lang="ts">
import { useI18n } from 'vue-i18n'

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
  <nav
    class="fixed inset-x-0 bottom-0 z-50
           border-t border-fino-border bg-fino-surface
           px-2 pt-2 pb-[calc(env(safe-area-inset-bottom)+0.5rem)]
           shadow-[0_-4px_24px_rgba(0,0,0,0.05)]
           lg:hidden"
    :aria-label="t('nav.menu')"
  >
    <div class="mx-auto grid max-w-lg grid-cols-4 gap-1">
      <RouterLink
        v-for="item in navigation"
        :key="item.to"
        v-slot="{ href, navigate, isActive }"
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
          :aria-current="isActive ? 'page' : undefined"
          @click="navigate"
        >
          <span
            class="flex h-9 w-12 items-center justify-center
                   rounded-xl transition-colors duration-200"
            :class="
              isActive ? 'bg-fino-accent' : 'bg-transparent'
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
            :class="isActive ? 'font-semibold' : 'font-medium'"
          >
            {{ t(item.label) }}
          </span>
        </a>
      </RouterLink>
    </div>
  </nav>
</template>