<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConfetti } from '@/app/composables/useConfetti'

const { t } = useI18n({ useScope: 'global' })
const { burst } = useConfetti()

// Превью кабинета: нажали «Закрыть разрыв» — хлопушка и разрыв закрыт
const isGapClosed = ref(false)

function closeGap(event: MouseEvent) {
  burst(event.currentTarget as HTMLElement)
  isGapClosed.value = true
}
</script>

<template>
  <div
    class="relative mx-auto w-full max-w-md lg:max-w-none"
    role="group"
    :aria-label="t('landing.preview.label')"
  >
    <!-- Прогноз остатка -->
    <div
      class="relative card-key p-5 sm:p-6"
      aria-hidden="true"
    >
      <div class="flex items-center justify-between gap-3">
        <span class="inline-flex items-center gap-1.5 rounded-full bg-fino-accent px-3 py-1 text-xs font-semibold text-primary">
          <i class="pi pi-eye text-xs" />
          {{ t('landing.preview.forecast') }}
        </span>

        <span class="text-xs text-fino-text-muted">
          {{ t('landing.preview.label') }}
        </span>
      </div>

      <p class="mt-4 text-xl font-display font-black text-fino-text sm:text-2xl">
        {{ t('landing.preview.gap') }}
      </p>

      <svg
        class="mt-4 h-28 w-full text-primary"
        viewBox="0 0 320 112"
        fill="none"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient
            id="landing-preview-fill"
            x1="0"
            y1="0"
            x2="0"
            y2="1"
          >
            <stop
              offset="0%"
              stop-color="currentColor"
              stop-opacity="0.18"
            />
            <stop
              offset="100%"
              stop-color="currentColor"
              stop-opacity="0"
            />
          </linearGradient>
        </defs>
        <line
          x1="0"
          y1="84"
          x2="320"
          y2="84"
          class="stroke-fino-border"
          stroke-dasharray="4 4"
        />
        <path
          d="M0 40 L56 22 L84 64 L112 56 L140 92 L170 70 L230 38 L260 58 L320 26 L320 112 L0 112 Z"
          fill="url(#landing-preview-fill)"
        />
        <path
          d="M0 40 L56 22 L84 64 L112 56 L140 92 L170 70 L230 38 L260 58 L320 26"
          stroke="currentColor"
          stroke-width="2.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle
          cx="140"
          cy="92"
          r="6"
          class="fill-primary stroke-fino-surface"
          stroke-width="3"
        />
      </svg>

      <button
        type="button"
        class="mt-4 inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl px-4 text-sm
               font-semibold btn-key focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :class="isGapClosed ? 'bg-fino-lime text-[#111]' : 'bg-primary text-primary-contrast'"
        @click="closeGap"
      >
        {{ isGapClosed ? t('landing.preview.gapClosed') : t('landing.preview.closeGap') }}
        <i
          :class="isGapClosed ? 'pi pi-check' : 'pi pi-arrow-right'"
          class="text-xs"
          aria-hidden="true"
        />
      </button>
    </div>

    <!-- Предодобренное предложение -->
    <div
      class="relative -mt-6 ml-6 flex items-center gap-4 rounded-2xl bg-fino-surface p-4 shadow-lg
             motion-safe:animate-fade-up sm:ml-12 sm:p-5 border-2 border-fino-line"
      aria-hidden="true"
    >
      <span class="flex size-11 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-primary border-2 border-fino-line">
        <i class="pi pi-wallet" />
      </span>

      <div class="min-w-0">
        <p class="text-xs text-fino-text-muted">
          {{ t('landing.preview.offerTitle') }}
        </p>
        <p class="break-words text-sm font-bold text-fino-text sm:text-base">
          {{ t('landing.preview.offerName') }} · {{ t('landing.preview.offerAmount') }}
        </p>
      </div>

      <span class="ml-auto shrink-0 text-sm font-semibold text-primary">
        {{ t('landing.preview.offerRate') }}
      </span>
    </div>
  </div>
</template>
