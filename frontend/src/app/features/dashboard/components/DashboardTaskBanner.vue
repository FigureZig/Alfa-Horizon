<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { useFormatters } from '@/app/composables/useFormatters'
import { TaskActionEnum } from '@/app/types/application/task-action-enum'
import type {
  ApplicationSummaryItemInterface,
  TaskInterface,
} from '@/app/types/application/applications-summary-interface'
import type { Nullable } from '@/app/types/nullable'

interface TaskRowInterface {
  id: string
  icon: string
  title: string
  due: string
  isUrgent: boolean
  to: Nullable<{ name: string; params: Record<string, string> }>
}

const URGENT_DAYS = 1

// Одна задача на заявку: подпись важнее голоса, голос важнее ответа банку
const ACTION_PRIORITY: Record<TaskActionEnum, number> = {
  [TaskActionEnum.Sign]: 0,
  [TaskActionEnum.Vote]: 1,
  [TaskActionEnum.AnswerInfo]: 2,
}
const UNKNOWN_PRIORITY = 3

const ACTION_ICONS: Record<TaskActionEnum, string> = {
  [TaskActionEnum.Sign]: 'pi pi-pen-to-square',
  [TaskActionEnum.Vote]: 'pi pi-users',
  [TaskActionEnum.AnswerInfo]: 'pi pi-comment',
}

const props = defineProps<{
  inn: string
  tasks: TaskInterface[]
  // Заявки компании: из них сумма, о которой задача
  applications: ApplicationSummaryItemInterface[]
  // Сегодня по часам мира, YYYY-MM-DD
  today: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatMoney, getDaysLeft } = useFormatters()

const isExpanded = ref(false)

function getPriority(task: TaskInterface): number {
  return task.action ? ACTION_PRIORITY[task.action] : UNKNOWN_PRIORITY
}

function getTitle(task: TaskInterface): string {
  const application = props.applications.find((item) => item.id === task.applicationId)

  if (!task.action || !application) return task.title

  return t(`dashboardTasks.action.${task.action}`, { amount: formatMoney(application.amount) })
}

function getDue(task: TaskInterface): { text: string; isUrgent: boolean } {
  if (!task.dueDate || !props.today) return { text: '', isUrgent: false }

  const daysLeft = getDaysLeft(task.dueDate, props.today)

  return {
    text: daysLeft === 0 ? t('dashboardTasks.dueToday') : t('dashboardTasks.daysLeft', daysLeft),
    isUrgent: daysLeft <= URGENT_DAYS,
  }
}

// Самое срочное — первым; по одной задаче на заявку
const rows = computed<TaskRowInterface[]>(() => {
  const byApplication = new Map<string, TaskInterface>()

  for (const task of props.tasks) {
    const key = task.applicationId ?? task.id
    const current = byApplication.get(key)

    if (!current || getPriority(task) < getPriority(current)) {
      byApplication.set(key, task)
    }
  }

  return [...byApplication.values()]
    .sort((a, b) => (a.dueDate ?? '9999').localeCompare(b.dueDate ?? '9999') || getPriority(a) - getPriority(b))
    .map((task) => {
      const due = getDue(task)

      return {
        id: task.id,
        icon: task.action ? ACTION_ICONS[task.action] : 'pi pi-check-square',
        title: getTitle(task),
        due: due.text,
        isUrgent: due.isUrgent,
        to: task.applicationId
          ? { name: 'application', params: { inn: props.inn, applicationId: task.applicationId } }
          : null,
      }
    })
})

const mainTask = computed(() => rows.value[0] ?? null)
const otherTasks = computed(() => rows.value.slice(1))

function toggleOthers() {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <section
    v-if="mainTask"
    class="animate-fade-up rounded-3xl border border-amber-500/30 bg-fino-amber-soft p-4 motion-reduce:animate-none sm:p-5"
    :aria-label="t('dashboardTasks.label')"
  >
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
      <span
        class="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-amber-500/15 text-amber-700
               dark:text-amber-400"
        aria-hidden="true"
      >
        <i
          :class="mainTask.icon"
          class="text-lg"
        />
      </span>

      <div class="min-w-0 flex-1">
        <p class="break-words text-base font-bold tracking-tight text-fino-text sm:text-lg">
          {{ mainTask.title }}
        </p>

        <p
          v-if="mainTask.due"
          class="mt-0.5 text-sm font-semibold"
          :class="mainTask.isUrgent ? 'text-amber-700 dark:text-amber-400' : 'text-fino-text-muted'"
        >
          {{ mainTask.due }}
        </p>
      </div>

      <RouterLink
        v-if="mainTask.to"
        :to="mainTask.to"
        class="inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm
               font-semibold text-primary-contrast focus-visible:outline-2 focus-visible:outline-offset-2
               focus-visible:outline-primary btn-key"
      >
        {{ t('dashboardTasks.open') }}
        <i
          class="pi pi-arrow-right text-xs"
          aria-hidden="true"
        />
      </RouterLink>
    </div>

    <template v-if="otherTasks.length">
      <button
        type="button"
        class="mt-3 inline-flex cursor-pointer items-center gap-1.5 text-sm font-semibold text-fino-text-muted
               transition-colors hover:text-fino-text focus-visible:outline-2 focus-visible:outline-primary
               sm:ml-15"
        :aria-expanded="isExpanded"
        @click="toggleOthers"
      >
        {{ t('dashboardTasks.more', otherTasks.length) }}
        <i
          class="pi pi-chevron-down text-xs transition-transform duration-200 motion-reduce:transition-none"
          :class="{ 'rotate-180': isExpanded }"
          aria-hidden="true"
        />
      </button>

      <ul
        v-if="isExpanded"
        class="mt-2 flex flex-col divide-y divide-amber-500/20 sm:ml-15"
      >
        <li
          v-for="task in otherTasks"
          :key="task.id"
        >
          <component
            :is="task.to ? RouterLink : 'div'"
            :to="task.to ?? undefined"
            class="group flex items-center gap-3 py-2.5 text-sm"
          >
            <i
              :class="task.icon"
              class="text-xs text-amber-700 dark:text-amber-400"
              aria-hidden="true"
            />
            <span class="min-w-0 flex-1 break-words font-semibold text-fino-text group-hover:text-primary">
              {{ task.title }}
            </span>
            <span class="shrink-0 text-xs text-fino-text-muted">{{ task.due }}</span>
          </component>
        </li>
      </ul>
    </template>
  </section>
</template>
