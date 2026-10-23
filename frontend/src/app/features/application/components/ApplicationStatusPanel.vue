<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationDecisionInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  status: ApplicationDetailStatusEnum
  decision: Nullable<ApplicationDecisionInterface>
  slaUntil: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

// Заголовок и «что сейчас» показывает ApplicationHero; здесь только причины, подсказки и действия
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
  <section class="flex flex-col gap-4 empty:hidden">
    <p
      v-if="slaText"
      class="flex items-center gap-2 text-sm text-fino-text-muted"
    >
      <i
        class="pi pi-clock text-xs"
        aria-hidden="true"
      />
      {{ slaText }}
    </p>

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
