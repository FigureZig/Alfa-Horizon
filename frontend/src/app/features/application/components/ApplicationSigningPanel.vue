<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFormatters } from '@/app/composables/useFormatters'
import { SigningModeEnum } from '@/app/types/application/signing-mode-enum'
import type {
  ApplicationSignatureInterface,
  ApplicationSignersInterface,
} from '@/app/types/application/application-interface'
import type { CompanyDirectorInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

interface SignerRowInterface {
  inn: string
  name: string
  // Время подписи; пусто — ещё не подписал
  signedAt: string
}

const props = defineProps<{
  signers: Nullable<ApplicationSignersInterface>
  signatures: ApplicationSignatureInterface[]
  // Руководители по реестру: имена тех, кто вправе подписать
  directors: CompanyDirectorInterface[]
}>()

const { t } = useI18n({ useScope: 'global' })
const { formatDateTime } = useFormatters()

const modeText = computed(() => (props.signers ? t(`application.signing.mode.${props.signers.mode}`) : ''))

// Кто подписывает и кто уже подписал; кто подписал, не будучи в списке (по доверенности), — тоже в списке
const rows = computed<SignerRowInterface[]>(() => {
  const expected = props.signers?.mode === SigningModeEnum.Joint ? props.signers.required : props.signers?.anyOf ?? []
  const inns = [...new Set([...expected, ...props.signatures.map((signature) => signature.inn)])]

  return inns.map((inn) => {
    const signature = props.signatures.find((item) => item.inn === inn)

    return {
      inn,
      name: signature?.fio ?? props.directors.find((director) => director.inn === inn)?.fullName ?? t('application.view.director'),
      signedAt: signature
        ? formatDateTime(signature.at, { day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit' })
        : '',
    }
  })
})
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
      v-if="rows.length"
      class="flex flex-col divide-y divide-fino-border rounded-2xl border border-fino-border px-4"
    >
      <li
        v-for="row in rows"
        :key="row.inn"
        class="flex items-center gap-3 py-3 text-sm"
      >
        <i
          :class="row.signedAt ? 'pi pi-check-circle text-green-600 dark:text-green-400' : 'pi pi-clock text-fino-text-muted'"
          aria-hidden="true"
        />

        <span class="min-w-0 flex-1 break-words text-fino-text">
          {{ row.name }}
        </span>

        <span class="shrink-0 text-xs text-fino-text-muted">
          {{ row.signedAt || t('application.signing.waiting') }}
        </span>
      </li>
    </ul>
  </section>
</template>
