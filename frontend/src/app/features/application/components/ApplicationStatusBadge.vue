<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'

const SUCCESS_CLASS = 'bg-green-500/10 text-green-700 dark:text-green-400'
const ATTENTION_CLASS = 'bg-fino-accent text-primary'
const DANGER_CLASS = 'bg-red-500/10 text-red-700 dark:text-red-400'
const NEUTRAL_CLASS = 'bg-fino-surface-secondary text-fino-text-muted'

const STATUS_CLASSES: Record<ApplicationDetailStatusEnum, string> = {
  [ApplicationDetailStatusEnum.Draft]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.Submitted]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.Checking]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.InfoRequested]: ATTENTION_CLASS,
  [ApplicationDetailStatusEnum.UnderReview]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.Offered]: ATTENTION_CLASS,
  [ApplicationDetailStatusEnum.Signing]: ATTENTION_CLASS,
  [ApplicationDetailStatusEnum.Signed]: SUCCESS_CLASS,
  [ApplicationDetailStatusEnum.Disbursing]: SUCCESS_CLASS,
  [ApplicationDetailStatusEnum.Issued]: SUCCESS_CLASS,
  [ApplicationDetailStatusEnum.Rejected]: DANGER_CLASS,
  [ApplicationDetailStatusEnum.Declined]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.Withdrawn]: NEUTRAL_CLASS,
  [ApplicationDetailStatusEnum.Expired]: DANGER_CLASS,
}

const props = defineProps<{
  status: ApplicationDetailStatusEnum
}>()

const { t } = useI18n({ useScope: 'global' })

const label = computed(() => t(`application.status.${props.status}`))
</script>

<template>
  <span
    class="inline-flex w-fit shrink-0 items-center rounded-lg px-2.5 py-1 text-xs font-semibold"
    :class="STATUS_CLASSES[status]"
  >
    {{ label }}
  </span>
</template>
