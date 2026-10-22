<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <aside
    class="relative flex flex-col-reverse items-center gap-6 overflow-hidden rounded-3xl
           bg-primary p-6 text-primary-contrast shadow-sm sm:flex-row-reverse
           sm:justify-between sm:px-10 sm:py-7"
  >
    <!-- Фоновые круги -->
    <div
      class="pointer-events-none absolute -top-16 -right-16 size-56 rounded-full bg-white/10"
      aria-hidden="true"
    />
    <div
      class="pointer-events-none absolute -bottom-20 -left-16 size-64 rounded-full bg-black/10"
      aria-hidden="true"
    />

    <!-- Иллюстрация: карточка персоны -->
    <svg
      class="relative w-36 shrink-0 sm:w-48 lg:w-56"
      viewBox="0 0 320 240"
      fill="none"
      role="img"
      :aria-label="t('sandbox.builder.promoImageLabel')"
    >
      <!-- Задняя карточка -->
      <rect
        x="52"
        y="20"
        width="220"
        height="170"
        rx="28"
        class="fill-white/25"
        transform="rotate(8 162 105)"
      />

      <!-- Основная карточка -->
      <rect
        x="36"
        y="36"
        width="220"
        height="170"
        rx="28"
        class="fill-white"
      />

      <!-- Аватар -->
      <circle
        cx="86"
        cy="86"
        r="26"
        class="fill-fino-accent"
      />
      <circle
        cx="86"
        cy="79"
        r="9"
        class="fill-primary"
      />
      <path
        d="M70 102c2-9 8-14 16-14s14 5 16 14c-4 4-10 6-16 6s-12-2-16-6Z"
        class="fill-primary"
      />

      <!-- Бейдж кода сценария -->
      <rect
        x="190"
        y="64"
        width="46"
        height="24"
        rx="12"
        class="fill-fino-accent"
      />
      <rect
        x="202"
        y="73"
        width="22"
        height="6"
        rx="3"
        class="fill-primary"
      />

      <!-- Строки данных -->
      <rect
        x="62"
        y="130"
        width="140"
        height="10"
        rx="5"
        class="fill-fino-text"
        opacity="0.85"
      />
      <rect
        x="62"
        y="152"
        width="110"
        height="8"
        rx="4"
        class="fill-fino-text-muted"
        opacity="0.5"
      />
      <rect
        x="62"
        y="172"
        width="150"
        height="8"
        rx="4"
        class="fill-fino-text-muted"
        opacity="0.5"
      />

      <!-- Галочка -->
      <circle
        cx="258"
        cy="196"
        r="32"
        class="fill-fino-text"
      />
      <path
        d="m243 196 11 11 20-22"
        class="stroke-white"
        stroke-width="7"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>

    <div class="relative min-w-0 flex-1 text-center sm:text-left">
      <p class="text-2xl font-bold leading-tight tracking-tight sm:text-3xl">
        {{ t('sandbox.builder.promoTitle') }}
      </p>

      <p class="mt-3 text-sm leading-relaxed text-white/80">
        {{ t('sandbox.builder.promoDescription') }}
      </p>
    </div>
  </aside>
</template>
