<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationDecisionInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

interface StatusViewInterface {
  icon: string
  iconClass: string
  isBusy?: boolean
}

const NEUTRAL_ICON = 'bg-fino-surface-secondary text-fino-text-muted'
const DANGER_ICON = 'bg-red-500/10 text-red-700 dark:text-red-400'

// Как выглядит каждый статус, у которого нет своей панели с действиями
const STATUS_VIEWS: Partial<Record<ApplicationDetailStatusEnum, StatusViewInterface>> = {
  [ApplicationDetailStatusEnum.Draft]: { icon: 'pi pi-file-edit', iconClass: NEUTRAL_ICON },
  [ApplicationDetailStatusEnum.Submitted]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL_ICON, isBusy: true },
  [ApplicationDetailStatusEnum.Checking]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL_ICON, isBusy: true },
  [ApplicationDetailStatusEnum.UnderReview]: { icon: 'pi pi-user', iconClass: NEUTRAL_ICON },
  [ApplicationDetailStatusEnum.Signed]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL_ICON, isBusy: true },
  [ApplicationDetailStatusEnum.Disbursing]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL_ICON, isBusy: true },
  [ApplicationDetailStatusEnum.Rejected]: { icon: 'pi pi-times-circle', iconClass: DANGER_ICON },
  [ApplicationDetailStatusEnum.Declined]: { icon: 'pi pi-ban', iconClass: NEUTRAL_ICON },
  [ApplicationDetailStatusEnum.Withdrawn]: { icon: 'pi pi-undo', iconClass: NEUTRAL_ICON },
  [ApplicationDetailStatusEnum.Expired]: { icon: 'pi pi-clock', iconClass: DANGER_ICON },
}

const props = defineProps<{
  status: ApplicationDetailStatusEnum
  decision: Nullable<ApplicationDecisionInterface>
  slaUntil: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

const view = computed(() => STATUS_VIEWS[props.status] ?? STATUS_VIEWS[ApplicationDetailStatusEnum.Checking])

const title = computed(() => t(`application.statusPanel.${props.status}.title`))
const description = computed(() => t(`application.statusPanel.${props.status}.description`))

const slaText = computed(() =>
  props.status === ApplicationDetailStatusEnum.UnderReview && props.slaUntil
    ? t('application.statusPanel.sla', {
      date: formatDateTime(props.slaUntil, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
    })
    : '',
)

// Причины и подсказки показываем только при отказе
const isRejected = computed(() => props.status === ApplicationDetailStatusEnum.Rejected)
const reasons = computed(() => (isRejected.value ? props.decision?.reasons ?? [] : []))
const hints = computed(() => (isRejected.value ? props.decision?.hints ?? [] : []))
</script>

<template>
  <section
    class="flex flex-col gap-4"
    :aria-busy="view?.isBusy"
  >
    <div class="flex items-start gap-4">
      <span
        class="flex size-12 shrink-0 items-center justify-center rounded-2xl"
        :class="view?.iconClass"
        aria-hidden="true"
      >
        <i
          :class="view?.icon"
          class="text-xl motion-reduce:animate-none"
        />
      </span>

      <div class="min-w-0">
        <h2 class="text-lg font-bold tracking-tight text-fino-text">
          {{ title }}
        </h2>

        <p class="mt-1 text-sm leading-relaxed text-fino-text-muted">
          {{ description }}
        </p>

        <p
          v-if="slaText"
          class="mt-2 text-xs text-fino-text-muted"
        >
          {{ slaText }}
        </p>
      </div>
    </div>

    <ul
      v-if="reasons.length"
      class="flex flex-col gap-2"
    >
      <li
        v-for="reason in reasons"
        :key="reason.code"
        class="flex items-start gap-2 rounded-xl bg-red-500/10 px-3 py-2 text-sm text-fino-text"
      >
        <i
          class="pi pi-exclamation-triangle mt-0.5 text-red-600 dark:text-red-400"
          aria-hidden="true"
        />
        <span class="min-w-0 break-words">{{ reason.text }}</span>
      </li>
    </ul>

    <div v-if="hints.length">
      <p class="text-xs font-semibold uppercase tracking-wide text-fino-text-muted">
        {{ t('application.statusPanel.hints') }}
      </p>

      <ul class="mt-2 flex flex-col gap-1.5">
        <li
          v-for="hint in hints"
          :key="hint"
          class="flex items-start gap-2 text-sm text-fino-text"
        >
          <i
            class="pi pi-lightbulb mt-0.5 text-primary"
            aria-hidden="true"
          />
          <span class="min-w-0 break-words">{{ hint }}</span>
        </li>
      </ul>
    </div>

    <slot />
  </section>
</template>
