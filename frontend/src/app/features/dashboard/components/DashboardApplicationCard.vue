<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DashboardOffersCardSkeleton from './DashboardOffersCardSkeleton.vue'
import { useApplicationSnapshot } from '@/app/composables/useApplicationSnapshot'
import { useApplicationStatusView } from '@/app/composables/useApplicationStatusView'
import { useCompanyAccess } from '@/app/composables/useCompanyAccess'
import { ApplicationStatusToneEnum } from '@/app/types/application/application-status-tone-enum'
import type { CompanyDirectorInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

const TONE_CLASSES: Record<ApplicationStatusToneEnum, string> = {
  [ApplicationStatusToneEnum.Neutral]: 'bg-fino-surface-secondary text-fino-text-muted',
  [ApplicationStatusToneEnum.Busy]: 'bg-fino-surface-secondary text-fino-text-muted',
  [ApplicationStatusToneEnum.Action]: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  [ApplicationStatusToneEnum.Success]: 'bg-green-500/10 text-green-700 dark:text-green-400',
  [ApplicationStatusToneEnum.Danger]: 'bg-red-500/10 text-red-700 dark:text-red-400',
}

const props = defineProps<{
  inn: string
  applicationId: string
  productName: string
  // Сколько ещё заявок в работе, кроме этой
  moreCount: number
  directors: CompanyDirectorInterface[]
  today: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { me } = useCompanyAccess(() => props.inn)
const { application, isLoading } = useApplicationSnapshot(() => props.applicationId)

// Тот же текст статуса, что и на странице заявки: что сейчас происходит для меня
const { view } = useApplicationStatusView(() =>
  application.value
    ? {
      application: application.value,
      explanation: null,
      personInn: me.value?.personInn ?? null,
      directors: props.directors,
      today: props.today,
    }
    : null,
)

const toneClass = computed(() => (view.value ? TONE_CLASSES[view.value.tone] : ''))
const applicationRoute = computed(() => ({
  name: 'application',
  params: { inn: props.inn, applicationId: props.applicationId },
}))
const applicationsRoute = computed(() => ({ name: 'applications', params: { inn: props.inn } }))
</script>

<template>
  <article
    class="flex min-w-0 flex-col gap-4 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm"
    :aria-label="t('dashboardOffers.applicationLabel')"
  >
    <h2 class="text-sm font-semibold text-fino-text">
      {{ t('dashboardOffers.applicationTitle', { name: productName }) }}
    </h2>

    <DashboardOffersCardSkeleton v-if="isLoading && !view" />

    <template v-else-if="view">
      <div class="flex items-start gap-3">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-xl"
          :class="toneClass"
          aria-hidden="true"
        >
          <i
            :class="view.icon"
            class="motion-reduce:animate-none"
          />
        </span>

        <div class="min-w-0">
          <p class="break-words text-base font-bold leading-snug tracking-tight text-fino-text">
            {{ view.title }}
          </p>

          <p
            v-if="view.subtitle"
            class="mt-1 break-words text-sm text-fino-text-muted"
          >
            {{ view.subtitle }}
          </p>

          <p
            v-if="view.deadline"
            class="mt-2 inline-flex items-center gap-1.5 rounded-full bg-fino-surface-secondary px-2.5 py-0.5
                   text-xs font-semibold text-fino-text"
          >
            <i
              class="pi pi-clock text-[10px]"
              aria-hidden="true"
            />
            {{ view.deadline }}
          </p>
        </div>
      </div>

      <div class="mt-auto flex flex-col gap-2">
        <RouterLink
          :to="applicationRoute"
          class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
                 font-semibold text-primary-contrast transition-all duration-200 hover:opacity-90 active:scale-95
                 motion-reduce:transition-none
                 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {{ t('dashboardOffers.openApplication') }}
          <i
            class="pi pi-arrow-right text-xs"
            aria-hidden="true"
          />
        </RouterLink>

        <RouterLink
          v-if="moreCount"
          :to="applicationsRoute"
          class="inline-flex min-h-10 items-center justify-center rounded-xl text-sm font-semibold
                 text-fino-text-muted transition-colors hover:text-fino-text"
        >
          {{ t('dashboardOffers.moreApplications', moreCount) }}
        </RouterLink>
      </div>
    </template>

    <!-- Подробности не загрузились — заявку всё равно можно открыть -->
    <RouterLink
      v-else
      :to="applicationRoute"
      class="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
    >
      {{ t('dashboardOffers.openApplication') }}
      <i
        class="pi pi-arrow-right text-xs"
        aria-hidden="true"
      />
    </RouterLink>
  </article>
</template>
