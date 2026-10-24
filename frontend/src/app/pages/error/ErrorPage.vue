<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, RouterLink } from 'vue-router'

type ErrorCode = 403 | 404 | 500

const route = useRoute()
const { t } = useI18n()

const errorCode = computed<ErrorCode>(() => {
  const code = Number(route.meta.errorCode)

  if (code === 403 || code === 500) {
    return code
  }

  return 404
})

const errorIcon = computed(() => {
  switch (errorCode.value) {
    case 403:
      return 'pi pi-lock'
    case 500:
      return 'pi pi-exclamation-triangle'
    default:
      return 'pi pi-search'
  }
})

const errorTitle = computed(() =>
    t(`errors.${errorCode.value}.title`),
)

const errorDescription = computed(() =>
    t(`errors.${errorCode.value}.description`),
)
</script>

<template>
  <main
    class="relative flex min-h-dvh items-center justify-center overflow-hidden bg-fino-surface-secondary px-4 py-12"
  >
    <!-- Background decoration -->
    <div
      class="pointer-events-none absolute -top-32 -right-32 h-96 w-96 rounded-full bg-fino-accent opacity-70 blur-3xl"
      aria-hidden="true"
    />

    <div
      class="pointer-events-none absolute -bottom-40 -left-32 h-96 w-96 rounded-full bg-fino-accent opacity-50 blur-3xl"
      aria-hidden="true"
    />

    <div
      class="relative z-10 w-full max-w-xl text-center"
    >
      <div
        class="card-key px-6 py-12 sm:px-12 sm:py-16"
      >
        <!-- Icon -->
        <div
          class="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-fino-accent sm:h-20 sm:w-20"
        >
          <i
            :class="errorIcon"
            class="text-3xl text-primary sm:text-4xl"
            aria-hidden="true"
          />
        </div>

        <!-- Error code -->
        <div
          class="mt-8 text-[100px] leading-none font-black tracking-tighter text-fino-text sm:text-[140px]"
          aria-hidden="true"
        >
          {{ errorCode }}
        </div>

        <!-- Text -->
        <h1
          class="mt-5 text-3xl font-black text-fino-text sm:text-5xl"
        >
          {{ errorTitle }}
        </h1>

        <p
          class="mx-auto mt-4 max-w-sm text-sm leading-7 text-fino-text-muted sm:text-base"
        >
          {{ errorDescription }}
        </p>

        <!-- Actions -->
        <div class="mt-9 flex flex-col justify-center gap-3 sm:flex-row">
          <RouterLink
            to="/"
            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-6 text-sm font-semibold text-white transition-opacity hover:opacity-90"
          >
            <i
              class="pi pi-home"
              aria-hidden="true"
            />
            {{ t('errors.goHome') }}
          </RouterLink>

          <RouterLink
            :to="{ name: 'login' }"
            class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-fino-surface px-6 text-sm font-semibold
          text-fino-text hover:bg-fino-surface-hover btn-key"
          >
            <i
              class="pi pi-sign-in text-primary"
              aria-hidden="true"
            />
            {{ t('errors.goLogin') }}
          </RouterLink>
        </div>
      </div>

      <!-- Footer -->
      <div class="mt-8 flex items-center justify-center gap-2">
        <span class="h-2 w-2 rounded-full bg-primary" />
        <span class="text-sm font-bold tracking-tight text-fino-text">
          Fino
        </span>
        <span class="text-xs text-fino-text-muted">
          · {{ t('errors.footer') }}
        </span>
      </div>
    </div>
  </main>
</template>