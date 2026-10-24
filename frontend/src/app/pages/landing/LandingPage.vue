<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppDotField from '@/app/components/AppDotField.vue'
import AppErrorState from '@/app/components/AppErrorState.vue'
import AppHeader from '@/app/components/layout/AppHeader.vue'
import LandingHeroPreview from '@/app/features/landing/components/LandingHeroPreview.vue'
import LandingProductCard from '@/app/features/landing/components/LandingProductCard.vue'
import LandingProductCardSkeleton from '@/app/features/landing/components/LandingProductCardSkeleton.vue'
import { useCatalogProducts } from '@/app/composables/useCatalogProducts'

const PRODUCT_SKELETON_COUNT = 3

// У каждого тезиса свой акцент макета: карточки не сливаются в одинаковый ряд
const POINTS = [
  { key: 'noForms', icon: 'pi pi-database', tone: 'bg-fino-lime text-[#111] -rotate-3' },
  { key: 'foresight', icon: 'pi pi-chart-line', tone: 'bg-fino-violet text-white rotate-2' },
  { key: 'decision', icon: 'pi pi-bolt', tone: 'bg-fino-blue text-white -rotate-2' },
] as const

const STEPS = ['need', 'offer', 'sign'] as const

const { t } = useI18n({ useScope: 'global' })
const { products, isLoading, error, loadProducts } = useCatalogProducts()
</script>

<template>
  <!-- isolate: фон из точек (z -10) рисуется над цветом страницы, но под содержимым -->
  <div class="relative isolate min-h-screen bg-fino-surface-secondary">
    <AppDotField />

    <AppHeader>
      <template #profile>
        <RouterLink
          :to="{ name: 'login' }"
          class="inline-flex h-10 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-contrast
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary btn-key"
        >
          {{ t('landing.nav.login') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </RouterLink>
      </template>
    </AppHeader>

    <main class="overflow-x-clip">
      <!-- Первый экран -->
      <section class="relative">
        <div
          class="relative mx-auto grid max-w-[1600px] grid-cols-1 items-center gap-12 px-4 pt-12 pb-16
                 sm:px-6 sm:pt-16 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-16 lg:pt-24 lg:pb-24"
        >
          <div class="min-w-0 motion-safe:animate-fade-up">
            <span
              class="inline-flex items-center gap-2 rounded-full border-2 border-fino-line bg-fino-surface px-3 py-1.5
                     font-mono text-xs font-bold uppercase tracking-wider text-fino-text"
            >
              <span
                class="size-1.5 rounded-full bg-primary"
                aria-hidden="true"
              />
              {{ t('landing.hero.eyebrow') }}
            </span>

            <h1 class="mt-6 max-w-3xl text-5xl font-black text-balance text-fino-text sm:text-6xl lg:text-7xl">
              {{ t('landing.hero.title') }}
            </h1>

            <p class="mt-6 max-w-xl text-base leading-relaxed text-fino-text-muted sm:text-lg">
              {{ t('landing.hero.description') }}
            </p>

            <div class="mt-8 flex flex-col gap-3 sm:flex-row">
              <RouterLink
                :to="{ name: 'login' }"
                class="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-6 text-base font-semibold
                       text-primary-contrast focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
                       btn-key"
              >
                {{ t('landing.hero.primary') }}
                <i
                  class="pi pi-arrow-right text-sm"
                  aria-hidden="true"
                />
              </RouterLink>

              <a
                href="#how-it-works"
                class="inline-flex min-h-12 items-center justify-center rounded-xl bg-fino-surface px-6 text-base font-semibold
                       text-fino-text hover:bg-fino-surface-hover focus-visible:outline-2
                       focus-visible:outline-offset-2 focus-visible:outline-primary btn-key"
              >
                {{ t('landing.hero.secondary') }}
              </a>
            </div>
          </div>

          <LandingHeroPreview />
        </div>
      </section>

      <!-- Три тезиса -->
      <section
        class="mx-auto max-w-[1600px] px-4 sm:px-6"
        :aria-label="t('landing.points.title')"
      >
        <ul class="grid gap-4 md:grid-cols-3">
          <li
            v-for="point in POINTS"
            :key="point.key"
            class="card-key p-6"
          >
            <span
              class="flex size-12 items-center justify-center rounded-2xl border-2 border-fino-line text-lg"
              :class="point.tone"
            >
              <i
                :class="point.icon"
                aria-hidden="true"
              />
            </span>

            <h2 class="mt-5 text-2xl font-black text-fino-text">
              {{ t(`landing.points.${point.key}.title`) }}
            </h2>

            <p class="mt-2 text-sm leading-relaxed text-fino-text-muted">
              {{ t(`landing.points.${point.key}.text`) }}
            </p>
          </li>
        </ul>
      </section>

      <!-- Как это работает -->
      <section
        id="how-it-works"
        class="mx-auto max-w-[1600px] scroll-mt-28 px-4 py-16 sm:px-6 lg:py-24"
      >
        <h2 class="text-4xl font-black text-fino-text sm:text-5xl">
          {{ t('landing.how.title') }}
        </h2>

        <ol class="mt-8 grid gap-4 md:grid-cols-3">
          <li
            v-for="(step, index) in STEPS"
            :key="step"
            class="relative card-key p-6"
          >
            <span
              class="flex size-12 -rotate-6 items-center justify-center rounded-2xl border-2 border-fino-line bg-primary
                     font-display text-2xl font-black text-primary-contrast shadow-[3px_3px_0_var(--fino-shadow)]"
              aria-hidden="true"
            >
              {{ index + 1 }}
            </span>

            <h3 class="mt-5 text-2xl font-black text-fino-text">
              {{ t(`landing.how.steps.${step}.title`) }}
            </h3>

            <p class="mt-2 text-sm leading-relaxed text-fino-text-muted">
              {{ t(`landing.how.steps.${step}.text`) }}
            </p>
          </li>
        </ol>
      </section>

      <!-- Продукты -->
      <section
        class="mx-auto max-w-[1600px] px-4 sm:px-6"
        :aria-label="t('landing.products.title')"
      >
        <div class="max-w-2xl">
          <h2 class="text-4xl font-black text-fino-text sm:text-5xl">
            {{ t('landing.products.title') }}
          </h2>

          <p class="mt-2 text-sm leading-relaxed text-fino-text-muted sm:text-base">
            {{ t('landing.products.description') }}
          </p>
        </div>

        <div
          v-if="isLoading && !products.length"
          class="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3"
          aria-busy="true"
        >
          <LandingProductCardSkeleton
            v-for="index in PRODUCT_SKELETON_COUNT"
            :key="index"
          />
        </div>

        <AppErrorState
          v-else-if="error"
          class="mt-8"
          :message="t('landing.products.loadError')"
          @retry="loadProducts"
        />

        <ul
          v-else
          class="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3"
        >
          <li
            v-for="product in products"
            :key="product.code"
          >
            <LandingProductCard :product="product" />
          </li>
        </ul>
      </section>

      <!-- Призыв -->
      <section class="mx-auto max-w-[1600px] px-4 py-16 sm:px-6 lg:py-24">
        <div
          class="relative overflow-hidden card-key bg-primary px-6 py-12 text-center text-primary-contrast sm:px-12
                 sm:py-16"
        >
          <!-- Наклонные стикеры по углам, как в макете -->
          <span
            class="pointer-events-none absolute top-6 left-6 hidden -rotate-6 rounded-xl border-2 border-[#111] bg-fino-lime
                   px-3 py-1 font-display text-lg font-black text-[#111] shadow-[3px_3px_0_#111] sm:inline-block"
            aria-hidden="true"
          >
            {{ t('landing.cta.stickerLeft') }}
          </span>
          <span
            class="pointer-events-none absolute right-6 bottom-6 hidden rotate-3 rounded-xl border-2 border-[#111]
                   bg-fino-violet px-3 py-1 font-display text-lg font-black text-white shadow-[3px_3px_0_#111] sm:inline-block"
            aria-hidden="true"
          >
            {{ t('landing.cta.stickerRight') }}
          </span>

          <h2 class="relative mx-auto max-w-3xl text-4xl font-black text-balance sm:text-6xl">
            {{ t('landing.cta.title') }}
          </h2>

          <p class="relative mx-auto mt-4 max-w-xl text-sm opacity-90 sm:text-base">
            {{ t('landing.cta.text') }}
          </p>

          <RouterLink
            :to="{ name: 'login' }"
            class="relative mt-8 inline-flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-white px-8
                   font-display text-lg font-extrabold text-[#111] btn-key [--fino-line:#111] [--fino-shadow:#111]
                   focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            {{ t('landing.cta.button') }}
            <i
              class="pi pi-arrow-right text-sm"
              aria-hidden="true"
            />
          </RouterLink>
        </div>
      </section>
    </main>

    <footer class="mx-auto max-w-[1600px] px-4 pb-10 text-center text-xs text-fino-text-muted sm:px-6">
      {{ t('landing.footer') }}
    </footer>
  </div>
</template>
