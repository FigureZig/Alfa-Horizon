<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTheme } from '@/app/composables/useTheme'

// Логотип всегда ведёт на главную продукта: главная кабинета — первый пункт меню
const HOME_ROUTE = { name: 'landing' }

const { theme, toggleTheme } = useTheme()
const { t, locale } = useI18n({ useScope: 'global' })

const isDark = computed(() => theme.value === 'dark')

function toggleLocale() {
  locale.value = locale.value === 'ru' ? 'en' : 'ru'

  localStorage.setItem('fino-locale', locale.value)
  document.documentElement.lang = locale.value
}

// Цвета старой темы уходят в центр кнопки
function changeTheme(event: MouseEvent) {
  const button = event.currentTarget as HTMLElement
  const rect = button.getBoundingClientRect()

  toggleTheme({ x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 })
}
</script>

<template>
  <header
    class="sticky top-0 z-50 px-4 pt-4 sm:px-6
           motion-safe:animate-header-appear"
  >
    <div
      class="mx-auto flex h-19 max-w-[1600px] items-center justify-between gap-3 card-key px-3 sm:px-5"
    >
      <!-- Логотип -->
      <RouterLink
        :to="HOME_ROUTE"
        class="group flex min-w-0 items-center gap-3"
        :aria-label="t('header.home')"
      >
        <div
          class="flex size-11 shrink-0 -rotate-3 items-center justify-center rounded-2xl border-2 border-fino-line
                 bg-primary text-primary-contrast shadow-[3px_3px_0_var(--fino-shadow)] transition-transform
                 duration-200 group-hover:rotate-0 motion-reduce:transition-none"
        >
          <span class="font-display text-xl font-black">F.</span>
        </div>

        <div class="hidden flex-col sm:flex">
          <span class="font-display text-xl font-black tracking-tight text-fino-text">
            fino
          </span>

          <span class="font-mono text-[10px] font-semibold uppercase tracking-wider text-fino-text-muted">
            {{ t('header.tagline') }}
          </span>
        </div>
      </RouterLink>

      <!-- Кнопки справа -->
      <div class="flex shrink-0 items-center gap-1.5 sm:gap-2">
        <!-- Язык -->
        <button
          type="button"
          class="flex h-10 cursor-pointer items-center justify-center
                 gap-2 rounded-xl border-2 border-fino-line bg-fino-surface
                 px-2.5 text-fino-text transition-colors duration-200
                 hover:bg-fino-lime hover:text-[#111]
                 focus-visible:outline-2 focus-visible:outline-primary
                 sm:px-3"
          :aria-label="t('common.language')"
          @click="toggleLocale"
        >
          <i
            class="pi pi-globe"
            aria-hidden="true"
          />

          <span class="text-sm font-semibold">
            {{ locale.toUpperCase() }}
          </span>
        </button>

        <!-- Тема -->
        <button
          type="button"
          class="flex size-10 cursor-pointer items-center justify-center
                 rounded-xl border-2 border-fino-line bg-fino-surface text-fino-text
                 transition-colors duration-200
                 hover:bg-fino-lime hover:text-[#111]
                 focus-visible:outline-2 focus-visible:outline-primary"
          :aria-label="
            isDark
              ? t('common.theme.light')
              : t('common.theme.dark')
          "
          :aria-pressed="isDark"
          @click="changeTheme"
        >
          <i
            :class="isDark ? 'pi pi-sun' : 'pi pi-moon'"
            aria-hidden="true"
          />
        </button>

        <!-- Профиль: страница подставляет своё содержимое; без него справа остаются язык и тема -->
        <slot name="profile" />
      </div>
    </div>
  </header>
</template>