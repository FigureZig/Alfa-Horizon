<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import ApplicationProgress from './ApplicationProgress.vue'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationDetailStatusEnum } from '@/app/types/application/application-detail-status-enum'
import type { ApplicationInterface } from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

interface ToneInterface {
  icon: string
  iconClass: string
  isBusy?: boolean
}

const URGENT_DAYS = 1

const NEUTRAL = 'bg-fino-surface-secondary text-fino-text-muted'
const ACCENT = 'bg-fino-accent text-primary'
const SUCCESS = 'bg-green-500/10 text-green-700 dark:text-green-400'
const DANGER = 'bg-red-500/10 text-red-700 dark:text-red-400'

// Иконка и цвет статуса: зелёный — хорошо, красный — отказ или срок, акцент — нужно ваше действие
const TONES: Record<ApplicationDetailStatusEnum, ToneInterface> = {
  [ApplicationDetailStatusEnum.Draft]: { icon: 'pi pi-file-edit', iconClass: NEUTRAL },
  [ApplicationDetailStatusEnum.Submitted]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL, isBusy: true },
  [ApplicationDetailStatusEnum.Checking]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL, isBusy: true },
  [ApplicationDetailStatusEnum.InfoRequested]: { icon: 'pi pi-comment', iconClass: ACCENT },
  [ApplicationDetailStatusEnum.UnderReview]: { icon: 'pi pi-user', iconClass: NEUTRAL },
  [ApplicationDetailStatusEnum.Offered]: { icon: 'pi pi-gift', iconClass: ACCENT },
  [ApplicationDetailStatusEnum.Signing]: { icon: 'pi pi-pen-to-square', iconClass: ACCENT },
  [ApplicationDetailStatusEnum.Signed]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL, isBusy: true },
  [ApplicationDetailStatusEnum.Disbursing]: { icon: 'pi pi-spinner pi-spin', iconClass: NEUTRAL, isBusy: true },
  [ApplicationDetailStatusEnum.Issued]: { icon: 'pi pi-check-circle', iconClass: SUCCESS },
  [ApplicationDetailStatusEnum.Rejected]: { icon: 'pi pi-times-circle', iconClass: DANGER },
  [ApplicationDetailStatusEnum.Declined]: { icon: 'pi pi-ban', iconClass: NEUTRAL },
  [ApplicationDetailStatusEnum.Withdrawn]: { icon: 'pi pi-undo', iconClass: NEUTRAL },
  [ApplicationDetailStatusEnum.Expired]: { icon: 'pi pi-clock', iconClass: DANGER },
}

const props = defineProps<{
  application: ApplicationInterface
  // Сегодняшняя дата мира, YYYY-MM-DD: срок считается по ней, а не по часам браузера
  today: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })
const { getDaysLeft } = useFormatters()

const status = computed(() => props.application.status)
const tone = computed(() => TONES[status.value])

// Голосование участников и дозапрос банка — разные ожидания в одном статусе
const isVoting = computed(
  () => status.value === ApplicationDetailStatusEnum.InfoRequested && Boolean(props.application.approval),
)

// Слово статуса и «что сейчас»: ключ зависит от исхода, а не только от статуса
const textKey = computed(() => {
  if (isVoting.value) return 'VOTING'
  if (status.value === ApplicationDetailStatusEnum.Issued) return props.application.loan?.isLimit ? 'ISSUED_LIMIT' : 'ISSUED'

  return status.value
})

const signedCount = computed(() => props.application.signatures.length)
const requiredCount = computed(() => props.application.signers?.required.length ?? 0)
const isJointSigning = computed(
  () => status.value === ApplicationDetailStatusEnum.Signing && requiredCount.value > 1,
)

const headline = computed(() => t(`application.hero.${textKey.value}.title`))

const now = computed(() =>
  isJointSigning.value
    ? t('application.hero.SIGNING_JOINT.now', { done: signedCount.value, total: requiredCount.value })
    : t(`application.hero.${textKey.value}.now`),
)

// Сколько дней осталось на текущем шаге
const daysLeft = computed(() => {
  const at = props.application.deadline?.at

  return at && props.today ? getDaysLeft(at, props.today) : null
})

const deadlineText = computed(() => {
  if (daysLeft.value === null) return ''

  return daysLeft.value === 0 ? t('application.hero.deadlineToday') : t('application.hero.deadline', daysLeft.value)
})

const isUrgent = computed(() => daysLeft.value !== null && daysLeft.value <= URGENT_DAYS)
</script>

<template>
  <section
    class="flex flex-col gap-6 rounded-3xl border border-fino-border bg-fino-surface p-5 shadow-sm sm:p-8"
    :aria-busy="tone.isBusy"
  >
    <div class="flex items-start gap-4 sm:gap-5">
      <span
        class="flex size-12 shrink-0 items-center justify-center rounded-2xl sm:size-14"
        :class="tone.iconClass"
        aria-hidden="true"
      >
        <i
          :class="tone.icon"
          class="text-xl sm:text-2xl motion-reduce:animate-none"
        />
      </span>

      <div class="min-w-0 flex-1">
        <h2 class="break-words text-xl font-bold tracking-tight text-balance text-fino-text sm:text-3xl">
          {{ headline }}
        </h2>

        <p class="mt-2 max-w-2xl break-words text-sm leading-relaxed text-fino-text-muted sm:text-base">
          {{ now }}
        </p>

        <p
          v-if="deadlineText"
          class="mt-3 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold sm:text-sm"
          :class="isUrgent ? 'bg-red-500/10 text-red-700 dark:text-red-400' : 'bg-fino-surface-secondary text-fino-text'"
        >
          <i
            class="pi pi-clock text-xs"
            aria-hidden="true"
          />
          {{ deadlineText }}
        </p>
      </div>
    </div>

    <ApplicationProgress :status="status" />
  </section>
</template>
