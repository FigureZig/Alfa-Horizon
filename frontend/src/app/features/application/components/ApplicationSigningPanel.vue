<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { ApplicationActionEnum } from '@/app/types/application/application-action-enum'
import { ApplicationFlagEnum } from '@/app/types/application/application-flag-enum'
import type {
  ApplicationSignatureInterface,
  ApplicationSignersInterface,
} from '@/app/types/application/application-interface'
import type { Nullable } from '@/app/types/nullable'

const props = defineProps<{
  signers: Nullable<ApplicationSignersInterface>
  signatures: ApplicationSignatureInterface[]
  flags: ApplicationFlagEnum[]
  canSign: boolean
  pendingAction: Nullable<ApplicationActionEnum>
  deadlineAt: Nullable<string>
  // Кого ещё ждём при совместной подписи (имена из профиля компании)
  pendingSigners: string[]
}>()

const emit = defineEmits<{
  sign: []
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

const isBusy = computed(() => props.pendingAction !== null)
const isSigning = computed(() => props.pendingAction === ApplicationActionEnum.Sign)
const isProvisional = computed(() => props.flags.includes(ApplicationFlagEnum.Provisional))

const modeText = computed(() => (props.signers ? t(`application.signing.mode.${props.signers.mode}`) : ''))

const signedList = computed(() =>
  props.signatures.map((signature) => ({
    inn: signature.inn,
    fio: signature.fio,
    role: t(`application.signing.role.${signature.role}`),
    at: formatDateTime(signature.at, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
  })),
)

const deadlineText = computed(() =>
  props.deadlineAt
    ? t('application.deadlineUntil', {
      date: formatDateTime(props.deadlineAt, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' }),
    })
    : '',
)

function handleSign() {
  emit('sign')
}
</script>

<template>
  <section class="flex flex-col gap-5">
    <div>
      <h2 class="text-lg font-bold tracking-tight text-fino-text">
        {{ t('application.signing.title') }}
      </h2>

      <p class="mt-1 text-sm text-fino-text-muted">
        {{ modeText }}
      </p>
    </div>

    <ul
      v-if="signedList.length"
      class="flex flex-col divide-y divide-fino-border rounded-2xl border border-fino-border px-4"
    >
      <li
        v-for="signature in signedList"
        :key="signature.inn"
        class="flex items-center gap-3 py-3 text-sm"
      >
        <i
          class="pi pi-check-circle text-green-600 dark:text-green-400"
          aria-hidden="true"
        />

        <span class="min-w-0 flex-1 break-words text-fino-text">
          {{ signature.fio }}
          <span class="text-xs text-fino-text-muted">· {{ signature.role }}</span>
        </span>

        <span class="shrink-0 text-xs text-fino-text-muted">
          {{ signature.at }}
        </span>
      </li>
    </ul>

    <ul
      v-if="pendingSigners.length"
      class="flex flex-col gap-2"
    >
      <li
        v-for="name in pendingSigners"
        :key="name"
        class="flex items-center gap-3 rounded-2xl border border-dashed border-fino-border px-4 py-3 text-sm"
      >
        <i
          class="pi pi-clock text-fino-text-muted"
          aria-hidden="true"
        />
        <span class="min-w-0 flex-1 break-words text-fino-text">{{ name }}</span>
        <span class="shrink-0 text-xs text-fino-text-muted">{{ t('application.signing.waiting') }}</span>
      </li>
    </ul>

    <p
      v-if="isProvisional"
      class="flex items-start gap-2 rounded-2xl bg-fino-accent p-3 text-sm text-fino-text"
    >
      <i
        class="pi pi-clock mt-0.5 text-primary"
        aria-hidden="true"
      />
      {{ t('application.signing.provisional') }}
    </p>

    <p
      v-else-if="!canSign"
      class="rounded-2xl bg-fino-surface-secondary p-3 text-sm text-fino-text-muted"
    >
      {{ t('application.signing.noRight') }}
    </p>

    <div class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-xs text-fino-text-muted">
        {{ deadlineText }}
      </p>

      <button
        v-if="canSign"
        type="button"
        class="inline-flex min-h-12 w-full cursor-pointer items-center justify-center gap-2 rounded-xl
               bg-primary px-5 py-3 text-sm font-semibold text-primary-contrast
               transition-all duration-200 hover:opacity-90 active:scale-95 sm:w-fit
               disabled:cursor-not-allowed disabled:opacity-60 motion-reduce:transition-none
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :disabled="isBusy"
        :aria-busy="isSigning"
        @click="handleSign"
      >
        <i
          :class="isSigning ? 'pi pi-spinner pi-spin' : 'pi pi-pen-to-square'"
          class="text-xs"
          aria-hidden="true"
        />
        {{ t('application.signing.sign') }}
      </button>
    </div>
  </section>
</template>
