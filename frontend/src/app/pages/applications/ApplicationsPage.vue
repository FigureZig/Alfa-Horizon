<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationCard from '@/app/features/application/components/ApplicationCard.vue'
import ApplicationCardSkeleton from '@/app/features/application/components/ApplicationCardSkeleton.vue'
import { useApplications } from '@/app/composables/useApplications'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'

const APPLICATION_SKELETON_COUNT = 3
// Заявка закончилась: денег выдали, отказали, отозвали или срок предложения вышел
const CLOSED_STATUSES: ApplicationDetailStatusEnum[] = [
  ApplicationDetailStatusEnum.Issued,
  ApplicationDetailStatusEnum.Rejected,
  ApplicationDetailStatusEnum.Declined,
  ApplicationDetailStatusEnum.Withdrawn,
  ApplicationDetailStatusEnum.Expired,
]

const props = defineProps<{
  inn: string
}>()

const { t } = useI18n({ useScope: 'global' })
const { applications, isLoading, error, loadApplications } = useApplications(() => props.inn)

// Сначала то, что ждёт человека, потом — что ждёт банк, в конце — история
const groups = computed(() => {
  const needsAction = applications.value.filter((application) => application.availableActions.length > 0)
  const rest = applications.value.filter((application) => !application.availableActions.length)

  return [
    { key: 'needsAction', items: needsAction },
    { key: 'inProgress', items: rest.filter((application) => !CLOSED_STATUSES.includes(application.status)) },
    { key: 'closed', items: rest.filter((application) => CLOSED_STATUSES.includes(application.status)) },
  ].filter((group) => group.items.length)
})
</script>

<template>
  <div class="flex min-w-0 flex-col gap-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-fino-text sm:text-3xl">
          {{ t('application.title') }}
        </h1>

        <p class="mt-2 text-sm text-fino-text-muted">
          {{ t('application.description') }}
        </p>
      </div>

      <RouterLink
        :to="{ name: 'application-new', params: { inn } }"
        class="inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5
               text-sm font-semibold text-primary-contrast transition-all duration-200
               hover:opacity-90 active:scale-95 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        <i
          class="pi pi-plus text-xs"
          aria-hidden="true"
        />
        {{ t('application.newApplication') }}
      </RouterLink>
    </div>

    <div
      v-if="isLoading && !applications.length"
      class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
      aria-busy="true"
    >
      <ApplicationCardSkeleton
        v-for="index in APPLICATION_SKELETON_COUNT"
        :key="index"
      />
    </div>

    <AppErrorState
      v-else-if="error"
      :message="t('application.loadError')"
      @retry="loadApplications"
    />

    <div
      v-else-if="!applications.length"
      class="flex flex-col items-center rounded-3xl border border-dashed
             border-fino-border bg-fino-surface px-6 py-12 text-center"
    >
      <div class="flex size-14 items-center justify-center rounded-2xl bg-fino-accent text-primary">
        <i
          class="pi pi-file-edit text-2xl"
          aria-hidden="true"
        />
      </div>

      <p class="mt-4 text-base font-semibold text-fino-text">
        {{ t('application.empty') }}
      </p>

      <p class="mt-1 max-w-sm text-sm text-fino-text-muted">
        {{ t('application.emptyHint') }}
      </p>

      <RouterLink
        :to="{ name: 'credits', params: { inn } }"
        class="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary
               transition-opacity hover:opacity-80"
      >
        {{ t('application.findCredit') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </RouterLink>
    </div>

    <div
      v-else
      class="flex flex-col gap-8"
    >
      <section
        v-for="group in groups"
        :key="group.key"
        class="flex flex-col gap-3"
        :aria-labelledby="`applications-${group.key}`"
      >
        <div>
          <h2
            :id="`applications-${group.key}`"
            class="flex items-center gap-2 text-lg font-bold tracking-tight text-fino-text"
          >
            {{ t(`application.groups.${group.key}.title`) }}
            <span class="text-fino-text-muted">· {{ group.items.length }}</span>
          </h2>

          <p class="mt-0.5 text-sm text-fino-text-muted">
            {{ t(`application.groups.${group.key}.hint`) }}
          </p>
        </div>

        <ul class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <li
            v-for="application in group.items"
            :key="application.id"
            class="flex"
          >
            <ApplicationCard
              class="w-full"
              :application="application"
              :inn="inn"
            />
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
