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

function getActivityBadge(profile: CompanyProfileInterface): string {
  const activity = profile.activity

  if (!activity) return ''

  return activity.name
    ? t('companyInsights.activity', { name: activity.name, code: activity.okvedCode })
    : t('companyInsights.activityCode', { code: activity.okvedCode })
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

// «ЕГРЮЛ, ФНС и счёт в банке · 21.10, 14:02»
const sourcesLine = computed(() => {
  const profile = props.profile

  if (!profile) return ''

  const sources = profile.sources.map((source) => t(`companyInsights.source.${source}`))
  const updatedAt = profile.updatedAt
    ? formatDateTime(profile.updatedAt, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
    : ''

  return [sources.length ? formatList(sources) : '', updatedAt].filter(Boolean).join(' · ')
})

const isEmpty = computed(() => !badges.value.length && !sourcesLine.value)

function handleRetry() {
  emit('retry')
}
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border
           bg-fino-surface p-5 shadow-sm"
  >
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('companyInsights.title') }}
    </h2>

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
        class="mt-auto flex items-start gap-1.5 text-xs text-fino-text-muted"
      >
        <i
          class="pi pi-database mt-0.5 text-xs"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ sourcesLine }}</span>
      </p>
    </template>
  </article>
</template>
