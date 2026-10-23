<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { DecisionOfferKindEnum } from '@/app/types/application/decision-offer-kind-enum'
import type {
  ApplicationDecisionInterface,
  ApplicationOfferInterface,
  ApplicationRequestInterface,
} from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

const MAIN_VARIANT = 0

const props = defineProps<{
  offers: ApplicationOfferInterface[]
  request: ApplicationRequestInterface
  decision: Nullable<ApplicationDecisionInterface>
  canAccept: boolean
  canDecline: boolean
  pendingAction: Nullable<ApplicationActionEnum>
  deadlineAt: Nullable<string>
}>()

const emit = defineEmits<{
  accept: [variant: number]
  decline: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatPercent, formatDateTime } = useFormatters()

const isBusy = computed(() => props.pendingAction !== null)

const kindText = computed(() => {
  const kind = props.decision?.offerKind ?? DecisionOfferKindEnum.AsRequested

  return t(`application.offers.kind.${kind}`)
})

// Что банк изменил или потребовал: сумма, срок, продукт · поручительство, залог
const changes = computed(() => [
  ...(props.decision?.counter ?? []).map((code) => t(`application.offers.counter.${code}`)),
  ...(props.decision?.conditions ?? []).map((code) => t(`application.offers.condition.${code}`)),
])

// Встречное предложение: что просили и что предлагает банк — рядом, чтобы разница была видна сразу
const comparison = computed(() => {
  const main = props.offers[MAIN_VARIANT]

  if (!main) return null

  const isChanged = main.amount !== props.request.amount || (props.request.termMonths !== null && main.termMonths !== props.request.termMonths)

  if (!isChanged) return null

  return {
    requested: [formatCurrency(props.request.amount, 'RUB'), props.request.termMonths ? t('application.term', props.request.termMonths) : ''].filter(Boolean).join(' · '),
    proposed: [formatCurrency(main.amount, 'RUB'), t('application.term', main.termMonths)].join(' · '),
  }
})

const offerCards = computed(() =>
  props.offers.map((offer, index) => ({
    offer,
    variant: index,
    isMain: index === MAIN_VARIANT,
    amount: formatCurrency(offer.amount, 'RUB'),
    payment: formatCurrency(offer.payment, 'RUB'),
    rate: formatPercent(offer.rate),
  })),
)

const deadlineText = computed(() =>
  props.deadlineAt
    ? t('application.deadlineUntil', {
      date: formatDateTime(props.deadlineAt, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
    })
    : '',
)

// Какой вариант принимается прямо сейчас — для индикатора на нужной кнопке
const pendingVariant = ref(MAIN_VARIANT)

function isAccepting(variant: number): boolean {
  return props.pendingAction === ApplicationActionEnum.AcceptOffer && variant === pendingVariant.value
}

function handleAccept(variant: number) {
  pendingVariant.value = variant
  emit('accept', variant)
}

function handleDecline() {
  emit('decline')
}
</script>

<template>
  <section class="flex flex-col gap-5">
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('application.offers.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ kindText }}
      </p>

      <div
        v-if="comparison"
        class="mt-4 grid grid-cols-1 items-center gap-3 rounded-2xl bg-fino-surface-secondary p-4
               sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]"
      >
        <div class="min-w-0">
          <p class="text-xs text-fino-text-muted">
            {{ t('application.offers.requested') }}
          </p>
          <p class="mt-0.5 break-words text-base font-semibold text-fino-text-muted line-through decoration-fino-border">
            {{ comparison.requested }}
          </p>
        </div>

        <i
          class="pi pi-arrow-right hidden text-primary sm:block"
          aria-hidden="true"
        />

        <div class="min-w-0">
          <p class="text-xs text-fino-text-muted">
            {{ t('application.offers.proposed') }}
          </p>
          <p class="mt-0.5 break-words text-lg font-bold text-fino-text">
            {{ comparison.proposed }}
          </p>
        </div>
      </div>

      <ul
        v-if="changes.length"
        class="mt-3 flex flex-wrap gap-2"
      >
        <li
          v-for="change in changes"
          :key="change"
          class="rounded-lg bg-fino-accent px-2.5 py-1 text-xs font-semibold text-primary"
        >
          {{ change }}
        </li>
      </ul>
    </div>

    <ul
      class="grid grid-cols-1 gap-4"
      :class="{ 'lg:grid-cols-2': offerCards.length > 1 }"
    >
      <li
        v-for="card in offerCards"
        :key="card.variant"
        class="flex min-w-0 flex-col gap-4 rounded-2xl border p-4"
        :class="card.isMain ? 'border-primary' : 'border-fino-border'"
      >
        <div class="flex items-start justify-between gap-3">
          <p class="min-w-0 break-words text-sm font-semibold text-fino-text">
            {{ card.offer.productName }}
          </p>

          <span
            class="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-semibold"
            :class="card.isMain ? 'bg-primary text-primary-contrast' : 'bg-fino-surface-secondary text-fino-text-muted'"
          >
            {{ card.isMain ? t('application.offers.main') : t('application.offers.alternative') }}
          </span>
        </div>

        <p class="break-words text-3xl font-bold tracking-tight text-fino-text">
          {{ card.amount }}
        </p>

        <dl class="grid grid-cols-3 gap-3 text-xs">
          <div>
            <dt class="text-fino-text-muted">
              {{ t('application.offers.rate') }}
            </dt>
            <dd class="mt-0.5 text-sm font-semibold text-fino-text">
              {{ card.rate }}
            </dd>
          </div>

          <div>
            <dt class="text-fino-text-muted">
              {{ t('application.offers.termLabel') }}
            </dt>
            <dd class="mt-0.5 text-sm font-semibold text-fino-text">
              {{ t('application.term', card.offer.termMonths) }}
            </dd>
          </div>

          <div>
            <dt class="text-fino-text-muted">
              {{ t('application.offers.payment') }}
            </dt>
            <dd class="mt-0.5 text-sm font-semibold text-fino-text">
              {{ card.payment }}
            </dd>
          </div>
        </dl>

        <button
          v-if="canAccept"
          type="button"
          class="mt-auto inline-flex min-h-11 w-full cursor-pointer items-center justify-center gap-2
                 rounded-xl px-4 py-2.5 text-sm font-semibold transition-all duration-200 active:scale-95
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary
                 disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none"
          :class="card.isMain
            ? 'bg-primary text-primary-contrast hover:opacity-90'
            : 'border border-fino-border bg-fino-surface text-fino-text hover:bg-fino-surface-hover'"
          :disabled="isBusy"
          :aria-busy="isAccepting(card.variant)"
          @click="handleAccept(card.variant)"
        >
          <i
            v-if="isAccepting(card.variant)"
            class="pi pi-spinner pi-spin text-xs"
            aria-hidden="true"
          />
          {{ t('application.offers.accept') }}
        </button>
      </li>
    </ul>

    <div class="flex flex-wrap items-center justify-between gap-3 border-t border-fino-border pt-4">
      <p class="text-xs text-fino-text-muted">
        {{ deadlineText }}
      </p>

      <button
        v-if="canDecline"
        type="button"
        class="cursor-pointer text-sm font-semibold text-fino-text-muted transition-colors
               hover:text-primary disabled:cursor-not-allowed disabled:opacity-60
               focus-visible:outline-2 focus-visible:outline-primary"
        :disabled="isBusy"
        @click="handleDecline"
      >
        {{ t('application.offers.decline') }}
      </button>
    </div>
  </section>
</template>
