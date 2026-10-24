<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import DashboardOffersCardSkeleton from './DashboardOffersCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ExplanationPathOptionInterface } from '@/app/types/application/application-explanation-interface'
import type { CompanyBlockerInterface } from '@/app/types/company/company-blocker-interface'
import type { CreditProductInterface } from '@/app/types/company/credit-product-interface'
import type { Nullable } from '@/app/types/nullable'

const MAX_OFFERS = 2

const props = defineProps<{
  inn: string
  products: CreditProductInterface[]
  // Что мешает компании, если предложений нет
  blockers: CompanyBlockerInterface[]
  // Путь к одобрению из последнего отказа: что сделать и сколько тогда дадут
  fix: Nullable<ExplanationPathOptionInterface>
  rejectedApplicationId: Nullable<string>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  apply: [product: CreditProductInterface]
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatMoney, formatPercent } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.products.length)

const offers = computed(() =>
  props.products.slice(0, MAX_OFFERS).map((product) => {
    const rate = formatPercent(product.rate)

    return {
      product,
      terms: [
        t('dashboardOffers.amount', { amount: formatMoney(product.amount) }),
        product.isRateFrom ? t('dashboardOffers.rateFrom', { rate }) : rate,
      ].join(' · '),
      applyLabel: t('dashboardOffers.applyLabel', { name: product.name }),
    }
  }),
)

const isPreliminary = computed(() => props.products.some((product) => product.isPreliminary))

// Стоп-фактор: причина и что сделать; с суммой — если банк уже считал путь к одобрению по отказу
const fixText = computed(() => {
  const fix = props.fix

  if (!fix?.amount) return t('dashboardOffers.blockedFixGeneric')

  const amount = fix.rate !== null
    ? t('dashboardOffers.amountWithRate', { amount: formatMoney(fix.amount), rate: formatPercent(fix.rate) })
    : formatMoney(fix.amount)

  return t('dashboardOffers.blockedFix', { amount, action: fix.title })
})

const rejectedRoute = computed(() =>
  props.rejectedApplicationId
    ? { name: 'application', params: { inn: props.inn, applicationId: props.rejectedApplicationId } }
    : null,
)
const creditsRoute = computed(() => ({ name: 'credits', params: { inn: props.inn } }))

function handleApply(product: CreditProductInterface) {
  emit('apply', product)
}

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 card-key bg-fino-lime-soft p-5"
  >
    <h2 class="font-mono text-xs font-bold uppercase tracking-wider text-fino-text">
      {{ t('dashboardOffers.title') }}
    </h2>

    <DashboardOffersCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('dashboardOffers.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <!-- Стоп-фактор: причина и действие, а не пустой список -->
    <div
      v-else-if="!offers.length && blockers.length"
      class="flex flex-col gap-3"
    >
      <div class="flex items-start gap-3">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-xl bg-fino-accent text-red-700
                 dark:text-red-400"
          aria-hidden="true"
        >
          <i class="pi pi-ban" />
        </span>

        <div class="min-w-0">
          <p class="text-base font-bold leading-snug tracking-tight text-fino-text">
            {{ t('dashboardOffers.blockedTitle') }}
          </p>

          <ul class="mt-1 flex flex-col gap-1">
            <li
              v-for="blocker in blockers"
              :key="blocker.code"
              class="break-words text-sm text-fino-text-muted"
            >
              {{ blocker.text }}
            </li>
          </ul>
        </div>
      </div>

      <p class="flex items-start gap-2 rounded-2xl bg-fino-surface-secondary px-3 py-2.5 text-sm font-semibold text-fino-text">
        <i
          class="pi pi-arrow-right mt-1 text-xs text-primary"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ fixText }}</span>
      </p>

      <RouterLink
        v-if="rejectedRoute"
        :to="rejectedRoute"
        class="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        {{ t('dashboardOffers.blockedDetails') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </RouterLink>
    </div>

    <!-- Предложений нет и ничего не мешает: подбор под задачу -->
    <div
      v-else-if="!offers.length"
      class="flex flex-col gap-2"
    >
      <p class="text-sm text-fino-text-muted">
        {{ t('dashboardOffers.empty') }}
      </p>

      <RouterLink
        :to="creditsRoute"
        class="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        {{ t('dashboardOffers.findCredit') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </RouterLink>
    </div>

    <template v-else>
      <ul class="flex flex-col divide-y-2 divide-fino-line/15">
        <li
          v-for="offer in offers"
          :key="offer.product.id"
          class="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
        >
          <div class="min-w-0 flex-1">
            <p class="break-words font-display text-base font-extrabold text-fino-text">
              {{ offer.product.name }}
            </p>

            <p class="mt-0.5 break-words text-xs text-fino-text-muted">
              {{ offer.terms }}
            </p>
          </div>

          <button
            type="button"
            class="shrink-0 cursor-pointer rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-contrast
                   btn-key focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            :aria-label="offer.applyLabel"
            @click="handleApply(offer.product)"
          >
            {{ t('dashboardOffers.apply') }}
          </button>
        </li>
      </ul>

      <p
        v-if="isPreliminary"
        class="mt-auto flex items-center gap-1.5 text-xs text-fino-text-muted"
      >
        <i
          class="pi pi-info-circle text-xs"
          aria-hidden="true"
        />
        {{ t('dashboardOffers.preliminary') }}
      </p>
    </template>
  </article>
</template>
