<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import AppErrorState from '@/app/components/AppErrorState.vue'
import ApplicationsAndTasksCardSkeleton from './ApplicationsAndTasksCardSkeleton.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationStatusEnum } from '@/app/types/application/application-status-enum'
import { TaskTypeEnum } from '@/app/types/application/task-type-enum'
import type { ApplicationsSummaryInterface } from '@/app/types/application/applications-summary-interface'
import type { Nullable } from '@/app/types/nullable'

// Статусы, где от клиента ждут действия, выделяем акцентом
const ATTENTION_STATUSES = [ApplicationStatusEnum.ActionRequired, ApplicationStatusEnum.Approved]

const TASK_ICONS: Record<TaskTypeEnum, string> = {
  [TaskTypeEnum.Signature]: 'pi pi-pen-to-square',
  [TaskTypeEnum.DocumentRequest]: 'pi pi-paperclip',
}

const props = defineProps<{
  inn: string
  summary: Nullable<ApplicationsSummaryInterface>
  isLoading: boolean
  hasError: boolean
  // Сегодняшняя дата мира: срок задачи показываем в днях
  today: Nullable<string>
}>()

const emit = defineEmits<{
  retry: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatCurrency, formatDate, getDaysLeft } = useFormatters()

const isSkeletonVisible = computed(() => props.isLoading && !props.summary)

const creditsRoute = computed(() => ({ name: 'credits', params: { inn: props.inn } }))
const applicationsRoute = computed(() => ({ name: 'applications', params: { inn: props.inn } }))

const applications = computed(() =>
  (props.summary?.applications ?? []).map((application) => ({
    id: application.id,
    title: application.productName,
    amount: formatCurrency(application.amount, application.currency),
    status: t(`applicationsTasks.status.${application.status}`),
    statusClass: ATTENTION_STATUSES.includes(application.status)
      ? 'bg-fino-accent text-primary'
      : 'bg-fino-surface-secondary text-fino-text-muted',
    to: { name: 'application', params: { inn: props.inn, applicationId: application.id } },
  })),
)

const tasks = computed(() =>
  (props.summary?.tasks ?? []).map((task) => ({
    id: task.id,
    title: task.title,
    icon: TASK_ICONS[task.type] ?? 'pi pi-check-square',
    // Задача ведёт к заявке, где её можно выполнить: подписать, ответить банку
    to: task.applicationId
      ? { name: 'application', params: { inn: props.inn, applicationId: task.applicationId } }
      : null,
    meta: [
      t(`applicationsTasks.taskType.${task.type}`),
      task.dueDate && props.today
        ? t('applicationsTasks.daysLeft', getDaysLeft(task.dueDate, props.today))
        : task.dueDate
          ? t('applicationsTasks.dueDate', { date: formatDate(task.dueDate, { day: 'numeric', month: 'long' }) })
          : '',
    ].filter(Boolean).join(' · '),
  })),
)

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
      {{ t('applicationsTasks.title') }}
    </h2>

    <ApplicationsAndTasksCardSkeleton v-if="isSkeletonVisible" />

    <AppErrorState
      v-else-if="hasError"
      :message="t('applicationsTasks.loadError')"
      is-inline
      @retry="handleRetry"
    />

    <div
      v-else
      class="flex flex-col divide-y divide-fino-border"
    >
      <!-- Заявки -->
      <section
        class="flex gap-3 pb-4"
        :aria-label="t('nav.applications')"
      >
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-xl
                 bg-fino-surface-secondary text-fino-text-muted"
          aria-hidden="true"
        >
          <i class="pi pi-file-edit text-sm" />
        </span>

        <div
          v-if="!applications.length"
          class="min-w-0"
        >
          <p class="text-sm font-semibold text-fino-text">
            {{ t('applicationsTasks.noApplications') }}
          </p>

          <RouterLink
            :to="creditsRoute"
            class="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-primary
                   transition-opacity hover:opacity-80"
          >
            {{ t('applicationsTasks.findCredit') }}
            <i
              class="pi pi-arrow-right text-[10px]"
              aria-hidden="true"
            />
          </RouterLink>
        </div>

        <div
          v-else
          class="min-w-0 flex-1"
        >
          <p class="text-sm font-semibold text-fino-text">
            {{ t('applicationsTasks.applicationsCount', applications.length) }}
          </p>

          <ul class="mt-2 flex flex-col gap-2">
            <li
              v-for="application in applications"
              :key="application.id"
            >
              <RouterLink
                :to="application.to"
                class="group flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg
                       focus-visible:outline-2 focus-visible:outline-primary"
              >
                <span class="min-w-0 break-words text-xs text-fino-text group-hover:text-primary">
                  {{ application.title }} · {{ application.amount }}
                </span>

                <span
                  class="rounded-md px-1.5 py-0.5 text-[11px] font-semibold"
                  :class="application.statusClass"
                >
                  {{ application.status }}
                </span>
              </RouterLink>
            </li>
          </ul>

          <RouterLink
            :to="applicationsRoute"
            class="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary
                   transition-opacity hover:opacity-80"
          >
            {{ t('applicationsTasks.allApplications') }}
            <i
              class="pi pi-arrow-right text-[10px]"
              aria-hidden="true"
            />
          </RouterLink>
        </div>
      </section>

      <!-- Задачи -->
      <section
        class="flex gap-3 pt-4"
        :aria-label="t('applicationsTasks.tasksLabel')"
      >
        <span
          class="flex size-9 shrink-0 items-center justify-center rounded-xl
                 bg-fino-surface-secondary text-fino-text-muted"
          aria-hidden="true"
        >
          <i class="pi pi-check-square text-sm" />
        </span>

        <div
          v-if="!tasks.length"
          class="min-w-0"
        >
          <p class="text-sm font-semibold text-fino-text">
            {{ t('applicationsTasks.noTasks') }}
          </p>

          <p class="mt-1 text-xs text-fino-text-muted">
            {{ t('applicationsTasks.noTasksHint') }}
          </p>
        </div>

        <div
          v-else
          class="min-w-0 flex-1"
        >
          <p class="text-sm font-semibold text-fino-text">
            {{ t('applicationsTasks.tasksCount', tasks.length) }}
          </p>

          <ul class="mt-2 flex flex-col gap-2">
            <li
              v-for="task in tasks"
              :key="task.id"
            >
              <component
                :is="task.to ? RouterLink : 'div'"
                :to="task.to ?? undefined"
                class="group flex items-start gap-2 rounded-lg focus-visible:outline-2 focus-visible:outline-primary"
              >
                <i
                  :class="task.icon"
                  class="mt-0.5 text-xs text-primary"
                  aria-hidden="true"
                />

                <div class="min-w-0">
                  <p
                    class="break-words text-xs text-fino-text"
                    :class="{ 'group-hover:text-primary': task.to }"
                  >
                    {{ task.title }}
                  </p>

                  <p class="text-[11px] text-fino-text-muted">
                    {{ task.meta }}
                  </p>
                </div>
              </component>
            </li>
          </ul>
        </div>
      </section>
    </div>
  </article>
</template>
