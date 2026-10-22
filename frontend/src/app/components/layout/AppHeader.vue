<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { useTheme } from '@/app/composables/useTheme'

const { theme, toggleTheme } = useTheme()
const { t, locale } = useI18n({ useScope: 'global' })

const route = useRoute()

const isDark = computed(() => theme.value === 'dark')

// В кабинете логотип ведёт на главную текущей демо-персоны (у сотрудника банка — в очередь), вне кабинета — к выбору персоны
const homeRoute = computed(() => {
  if (!route.params.inn) return { name: 'sandbox' }

  const isBankRoute = String(route.name ?? '').startsWith('bank-')

  return { name: isBankRoute ? 'bank-queue' : 'dashboard', params: { inn: route.params.inn } }
})

function toggleLocale() {
  locale.value = locale.value === 'ru' ? 'en' : 'ru'

  localStorage.setItem('fino-locale', locale.value)
  document.documentElement.lang = locale.value
}

function changeTheme() {
  toggleTheme()
}
</script>

<template>
  <header
    class="sticky top-0 z-50 px-4 pt-4 sm:px-6
           motion-safe:animate-[header-appear_450ms_ease-out_both]"
  >
    <div
      class="mx-auto flex h-19 max-w-[1600px] items-center
             justify-between gap-3 rounded-3xl
             border border-fino-border bg-fino-surface
             px-3 shadow-sm sm:px-5"
    >
      <!-- Логотип -->
      <RouterLink
        :to="homeRoute"
        class="group flex min-w-0 items-center gap-3"
        :aria-label="t('header.home')"
      >
        <div
          class="flex size-11 shrink-0 items-center justify-center
                 rounded-2xl bg-primary text-primary-contrast
                 transition-transform duration-200
                 group-hover:scale-105"
        >
          <span class="text-xl font-bold">F.</span>
        </div>

        <div class="hidden flex-col sm:flex">
          <span class="text-xl font-bold tracking-tight text-fino-text">
            fino
          </span>

          <span class="text-[10px] text-fino-text-muted">
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
                 gap-2 rounded-xl bg-fino-surface-secondary
                 px-2.5 text-fino-text transition-all duration-200
                 hover:-translate-y-0.5 hover:bg-fino-surface-hover
                 active:scale-95
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
                 rounded-xl bg-fino-surface-secondary text-fino-text
                 transition-all duration-200
                 hover:-translate-y-0.5 hover:bg-fino-surface-hover
                 active:scale-95
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

        <!-- Профиль (страницы могут заменить своим содержимым) -->
        <slot name="profile">
          <div
            class="flex size-10 items-center justify-center
                   rounded-xl bg-fino-accent text-primary"
            role="img"
            :aria-label="t('common.profile')"
          >
            <i
              class="pi pi-user"
              aria-hidden="true"
            />
          </div>
        </slot>
      </div>
    </div>
  </header>
</template>