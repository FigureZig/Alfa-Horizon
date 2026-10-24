<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import CompanyInsightsCardSkeleton from './CompanyInsightsCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import type { CompanyProfileInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  profile: Nullable<CompanyProfileInterface>
  isLoading: boolean
  hasError: boolean
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDateTime, formatList } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.profile)

function getRegistrationBadge(profile: CompanyProfileInterface): string {
  if (!profile.legalForm) return ''

  const form = t(`companyInsights.legalForm.${profile.legalForm}`)

  return profile.registeredAt
    ? t('companyInsights.registeredSince', { form, year: profile.registeredAt.slice(0, 4) })
    : form
}

// Вид деятельности словами клиента: «Кофейня», а не формулировка ОКВЭД
function getActivityBadge(profile: CompanyProfileInterface): string {
  const activity = profile.activity

  return activity?.title ?? activity?.name ?? ''
}

// Бейдж показываем, только если значение пришло от API
const badges = computed(() => {
  const profile = props.profile

  if (!profile) return []

  return [
    { key: 'registration', label: getRegistrationBadge(profile) },
    {
      key: 'activity',
      label: getActivityBadge(profile),
    },
    {
      key: 'tax',
      label: profile.taxRegime ? t(`companyInsights.taxRegime.${profile.taxRegime}`) : '',
    },
    {
      key: 'revenue',
      label: profile.monthlyRevenue !== null
        ? t('companyInsights.monthlyRevenue', { amount: formatCurrency(profile.monthlyRevenue, profile.currency, true) })
        : '',
    },
  ].filter((badge) => badge.label)
})

// «Откуда данные: реестр компаний, налоговая и счёт в банке · 21.10, 14:02»
const sourcesLine = computed(() => {
  const profile = props.profile

  if (!profile) return ''

  const sources = profile.sources.map((source) => t(`companyInsights.source.${source}`))
  const updatedAt = profile.updatedAt
    ? formatDateTime(profile.updatedAt, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : ''

  return [sources.length ? t('companyInsights.sourcesLine', { list: formatList(sources) }) : '', updatedAt]
    .filter(Boolean)
    .join(' · ')
})

const isEmpty = computed(() => !badges.value.length && !sourcesLine.value)

// Кратко в заголовке свёрнутого блока: чем занимается компания
const preview = computed(() => (props.profile ? getActivityBadge(props.profile) : ''))

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <!-- Подробности по запросу: свёрнуто, как «Как посчитали» -->
  <details class="group min-w-0 rounded-3xl card-key">
    <summary
      class="flex cursor-pointer items-center justify-between gap-3 rounded-3xl px-5 py-4 marker:content-none
             focus-visible:outline-2 focus-visible:outline-primary"
    >
      <span class="flex min-w-0 flex-wrap items-baseline gap-x-2">
        <span class="text-sm font-semibold text-fino-text">{{ t('companyInsights.title') }}</span>
        <span
          v-if="preview"
          class="truncate text-sm text-fino-text-muted"
        >{{ preview }}</span>
      </span>

      <i
        class="pi pi-chevron-down text-xs text-fino-text-muted transition-transform duration-200
               group-open:rotate-180 motion-reduce:transition-none"
        aria-hidden="true"
      />
    </summary>

    <div class="flex flex-col gap-4 px-5 pb-5">
      <CompanyInsightsCardSkeleton v-if="isSkeletonVisible" />

      <AppErrorState
        v-else-if="hasError"
        :message="t('companyInsights.loadError')"
        is-inline
        @retry="handleRetry"
      />

      <p
        v-else-if="isEmpty"
        class="text-sm text-fino-text-muted"
      >
        {{ t('companyInsights.empty') }}
      </p>

      <template v-else>
        <ul
          v-if="badges.length"
          class="flex flex-wrap gap-2"
        >
          <li
            v-for="badge in badges"
            :key="badge.key"
            class="max-w-full break-words rounded-lg bg-fino-surface-secondary px-2.5 py-1
                   text-xs font-medium text-fino-text"
          >
            {{ badge.label }}
          </li>
        </ul>

        <p
          v-if="sourcesLine"
          class="flex items-start gap-1.5 text-xs text-fino-text-muted"
        >
          <i
            class="pi pi-database mt-0.5 text-xs"
            aria-hidden="true"
          />
          <span class="min-w-0 break-words">{{ sourcesLine }}</span>
        </p>
      </template>
    </div>
  </details>
</template>
