<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type {
  ApplicationDecisionInterface,
  ApplicationOfferInterface,
  ApplicationRequestInterface,
} from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

// Не больше трёх вариантов: основное предложение и альтернативы
const MAX_OFFERS = 3
const MAIN_VARIANT = 0

const props = defineProps<{
  offers: ApplicationOfferInterface[]
  request: ApplicationRequestInterface
  decision: Nullable<ApplicationDecisionInterface>
  canAccept: boolean
  canDecline: boolean
  pendingAction: Nullable<ApplicationActionEnum>
}>()

const emit = defineEmits<{
  accept: [variant: number]
  decline: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatMoney, formatPercent, formatTerm } = useFormatters()

const selectedVariant = ref(MAIN_VARIANT)

const isBusy = computed(() => props.pendingAction !== null)
const isAccepting = computed(() => props.pendingAction === ApplicationActionEnum.AcceptOffer)

const visibleOffers = computed(() => props.offers.slice(0, MAX_OFFERS))

// Сверху — что просили и что дают: «Вы просили 10 млн ₽ — банк готов дать 3,2 млн ₽ на 2 года или 4,4 млн ₽ на 3 года»
const headline = computed(() => {
  const main = visibleOffers.value[MAIN_VARIANT]

  if (!main) return ''

  const isChanged = main.amount !== props.request.amount
    || (props.request.termMonths !== null && main.termMonths !== props.request.termMonths)

  if (!isChanged && visibleOffers.value.length === 1) return ''

  const variants = visibleOffers.value.map((offer) =>
    t('application.offers.variant', { amount: formatMoney(offer.amount), term: formatTerm(offer.termMonths) }))
  const last = variants.pop() ?? ''
  const options = variants.length ? t('application.offers.or', { first: variants.join(', '), last }) : last

  return t('application.offers.headline', { requested: formatMoney(props.request.amount), options })
})

// Условия банка, без которых выдачи не будет: поручительство, залог
const conditions = computed(() =>
  (props.decision?.conditions ?? []).map((code) => t(`application.offers.condition.${code}`)),
)

const cards = computed(() =>
  visibleOffers.value.map((offer, index) => {
    const isLimit = offer.product === CreditProductCodeEnum.Overdraft
    // Переплата за срок одной цифрой: платежи минус сумма; у овердрафта проценты только за использованные дни
    const overpayment = isLimit ? null : Math.max(offer.payment * offer.termMonths - offer.amount, 0)

    return {
      variant: index,
      isMain: index === MAIN_VARIANT,
      isSelected: index === selectedVariant.value,
      amount: formatMoney(offer.amount),
      term: formatTerm(offer.termMonths),
      rate: formatPercent(offer.rate),
      payment: isLimit ? '' : t('application.offers.paymentValue', { payment: formatMoney(offer.payment) }),
      cost: overpayment === null
        ? t('application.offers.limitCost')
        : t('application.offers.overpayment', { amount: formatMoney(overpayment) }),
    }
  }),
)

const selectedCard = computed(() => cards.value[selectedVariant.value] ?? cards.value[MAIN_VARIANT] ?? null)

function selectVariant(variant: number) {
  if (!isBusy.value) {
    selectedVariant.value = variant
  }
}

function handleAccept() {
  emit('accept', selectedVariant.value)
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

      <p
        v-if="headline"
        class="mt-1 text-sm leading-relaxed text-fino-text-muted sm:text-base"
      >
        {{ headline }}
      </p>

      <ul
        v-if="conditions.length"
        class="mt-3 flex flex-wrap gap-2"
      >
        <li
          v-for="condition in conditions"
          :key="condition"
          class="rounded-lg bg-fino-amber-soft px-2.5 py-1 text-xs font-semibold text-amber-700 dark:text-amber-400"
        >
          {{ condition }}
        </li>
      </ul>
    </div>

    <!-- Выбор варианта: карточка выбирается, главная кнопка одна -->
    <div
      class="grid grid-cols-1 gap-3"
      :class="{ 'sm:grid-cols-2': cards.length === 2, 'sm:grid-cols-3': cards.length >= 3 }"
      role="radiogroup"
      :aria-label="t('application.offers.title')"
    >
      <button
        v-for="card in cards"
        :key="card.variant"
        type="button"
        role="radio"
        :aria-checked="card.isSelected"
        class="flex min-w-0 cursor-pointer flex-col gap-3 rounded-2xl border p-4 text-left transition-all duration-200
               disabled:cursor-not-allowed motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :class="card.isSelected
          ? 'border-primary bg-fino-accent/50 shadow-sm ring-1 ring-primary'
          : 'border-fino-border bg-fino-surface hover:border-primary/40'"
        :disabled="isBusy"
        @click="selectVariant(card.variant)"
      >
        <span class="flex w-full items-center justify-between gap-2">
          <span class="text-xs font-semibold text-fino-text-muted">
            {{ card.isMain ? t('application.offers.main') : t('application.offers.alternative') }}
          </span>

          <span
            class="flex size-5 shrink-0 items-center justify-center rounded-full border-2"
            :class="card.isSelected ? 'border-primary bg-primary' : 'border-fino-border'"
            aria-hidden="true"
          >
            <i
              v-if="card.isSelected"
              class="pi pi-check text-[10px] text-primary-contrast"
            />
          </span>
        </span>

        <span class="break-words text-2xl font-display font-black text-fino-text sm:text-3xl">
          {{ card.amount }}
        </span>

        <span class="flex flex-col gap-1 text-sm">
          <span class="text-fino-text">{{ card.term }} · {{ card.rate }}</span>
          <span
            v-if="card.payment"
            class="text-fino-text-muted"
          >{{ card.payment }}</span>
          <span class="text-fino-text-muted">{{ card.cost }}</span>
        </span>
      </button>
    </div>

    <div
      v-if="canAccept || canDecline"
      class="flex flex-col gap-3 border-t border-fino-border pt-4 sm:flex-row sm:items-center sm:justify-between"
    >
      <button
        v-if="canAccept && selectedCard"
        type="button"
        class="inline-flex min-h-12 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-6 text-sm
               font-semibold text-primary-contrast disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2
               focus-visible:outline-offset-2 focus-visible:outline-primary btn-key"
        :disabled="isBusy"
        :aria-busy="isAccepting"
        @click="handleAccept"
      >
        <i
          v-if="isAccepting"
          class="pi pi-spinner pi-spin text-xs"
          aria-hidden="true"
        />
        {{ t('application.offers.acceptVariant', { amount: selectedCard.amount, term: selectedCard.term }) }}
      </button>

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
