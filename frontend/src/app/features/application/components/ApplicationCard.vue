<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ApplicationFlags from './ApplicationFlags.vue'
import ApplicationStatusBadge from './ApplicationStatusBadge.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { ApplicationInterface } from '@/app/types/application/application-interface'

const props = defineProps<{
  application: ApplicationInterface
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDateTime } = useFormatters()

// Показываем то, что предложил банк; пока решения нет — то, что просил клиент
const title = computed(() => props.application.offer?.productName ?? t(`application.product.${props.application.request.product}`))
const amount = computed(() => formatCurrency(props.application.offer?.amount ?? props.application.request.amount, 'RUB'))
const termMonths = computed(() => props.application.offer?.termMonths ?? props.application.request.termMonths)
const updatedAt = computed(() =>
  formatDateTime(props.application.updatedAt, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
)
const route = computed(() => ({ name: 'application', params: { inn: props.inn, applicationId: props.application.id } }))
const hasAction = computed(() => props.application.availableActions.length > 0)
</script>

<template>
  <RouterLink
    :to="route"
    class="group flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm transition-all duration-300
           hover:-translate-y-1 hover:shadow-md
           focus-visible:outline-2 focus-visible:outline-primary
           motion-reduce:transition-none motion-reduce:hover:translate-y-0"
  >
    <div class="flex items-start justify-between gap-3">
      <p class="min-w-0 break-words text-base font-bold tracking-tight text-fino-text">
        {{ title }}
      </p>

      <ApplicationStatusBadge :status="application.status" />
    </div>

    <div>
      <p class="break-words text-2xl font-bold tracking-tight text-fino-text">
        {{ amount }}
      </p>

      <p
        v-if="termMonths"
        class="mt-1 text-sm text-fino-text-muted"
      >
        {{ t('application.term', termMonths) }}
      </p>
    </div>

    <ApplicationFlags :flags="application.flags" />

    <div class="mt-auto flex items-center justify-between gap-3 border-t border-fino-border pt-3 text-xs">
      <span class="text-fino-text-muted">
        {{ t('application.updated', { date: updatedAt }) }}
      </span>

      <span
        v-if="hasAction"
        class="inline-flex items-center gap-1 font-semibold text-primary"
      >
        {{ t('application.needsAction') }}
        <i
          class="pi pi-arrow-right text-[10px] transition-transform duration-200
                 group-hover:translate-x-0.5"
          aria-hidden="true"
        />
      </span>
    </div>
  </RouterLink>
</template>
