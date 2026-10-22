<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CashForecastCard from './CashForecastCard.vue'
import CashForecastCardSkeleton from './CashForecastCardSkeleton.vue'
import CreditOfferCard from './CreditOfferCard.vue'
import CreditOfferCardSkeleton from './CreditOfferCardSkeleton.vue'
import { useCashForecast } from '@/app/composables/useCashForecast'
import { useFeatureFlags } from '@/app/composables/useFeatureFlags'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'

// Продукты K2 загружает страница: тот же ответ использует карточка «Предодобрено»
const props = defineProps<{
  inn: string
  products: CreditProductInterface[]
  isProductsLoading: boolean
  productsError: boolean
}>()

const emit = defineEmits<{
  retryProducts: []
}>()

const { t } = useI18n({ useScope: 'global' })
const router = useRouter()

const { isK2Enabled } = useFeatureFlags()
const {
  forecast,
  isForecastLoading,
  forecastError,
  hasCashGap,
  loadForecast,
} = useCashForecast(() => props.inn)

// Кредит предлагаем, только если K1 нашёл разрыв, а K2 вернул подходящее предложение
const recommendedProduct = computed(() =>
  hasCashGap.value
    ? props.products.find((product) => product.isRecommended) ?? null
    : null,
)

const isForecastSkeletonVisible = computed(() => isForecastLoading.value && !forecast.value)

// Колонка предложения нужна только при разрыве; без предложения K2 график занимает всю ширину
const isOfferVisible = computed(() =>
  isK2Enabled
  && hasCashGap.value
  && (props.isProductsLoading || props.productsError || Boolean(recommendedProduct.value)),
)

const isOfferSkeletonVisible = computed(() => props.isProductsLoading && !recommendedProduct.value)

function closeGap(product: CreditProductInterface) {
  router.push({
    name: 'applications',
    params: { inn: props.inn },
    query: { productId: product.id },
  })
}

function retryProducts() {
  emit('retryProducts')
}

function showCreditOptions() {
  router.push({ name: 'credits', params: { inn: props.inn } })
}
</script>

<template>
  <section
    class="grid grid-cols-1 items-stretch gap-4"
    :class="{ 'xl:grid-cols-[minmax(0,1fr)_22rem]': isOfferVisible }"
    :aria-label="t('cashForecast.sectionLabel')"
  >
    <!-- K1: прогноз остатка -->
    <CashForecastCardSkeleton v-if="isForecastSkeletonVisible" />

    <AppErrorState
      v-else-if="forecastError"
      :message="t('cashForecast.loadError')"
      @retry="loadForecast"
    />

    <CashForecastCard
      v-else-if="forecast"
      :forecast="forecast"
    />

    <div
      v-else
      class="flex flex-col items-center rounded-3xl border border-dashed
             border-fino-border bg-fino-surface px-6 py-10 text-center"
    >
      <div class="flex size-12 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-chart-line text-xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 max-w-sm text-sm text-fino-text-muted">
        {{ t('cashForecast.empty') }}
      </p>
    </div>

    <!-- K2: посчитанное предложение -->
    <template v-if="isOfferVisible">
      <CreditOfferCardSkeleton v-if="isOfferSkeletonVisible" />

      <AppErrorState
        v-else-if="productsError"
        :message="t('creditOffer.loadError')"
        @retry="retryProducts"
      />

      <CreditOfferCard
        v-else-if="recommendedProduct"
        :product="recommendedProduct"
        @close-gap="closeGap"
        @show-options="showCreditOptions"
      />
    </template>
  </section>
</template>
