<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ApplicationWorldChangeInterface } from '@/app/types/application/application-world-change-interface'
import type { Nullable } from '@/app/types/nullable'

const DIRECTOR_CHANGED = 'directorChanged'

const props = defineProps<{
  change: ApplicationWorldChangeInterface
  // Банк ещё пересчитывает: решения пока нет
  isRecalculating: boolean
  // Руководитель по свежему реестру — называем его при смене директора
  directorName: Nullable<string>
}>()

const { t } = useI18n({ useScope: 'global' })

const reason = computed(() =>
  props.change.reasonKey === DIRECTOR_CHANGED && props.directorName
    ? t('application.worldChange.reason.directorChangedName', { name: props.directorName })
    : t(`application.worldChange.reason.${props.change.reasonKey}`),
)

const consequence = computed(() => {
  if (props.isRecalculating) return t('application.worldChange.recalculating')

  return props.change.isSignatureReset ? t('application.worldChange.signaturesReset') : t('application.worldChange.recalculated')
})
</script>

<template>
  <section
    class="flex animate-fade-up items-start gap-3 rounded-2xl bg-fino-amber-soft p-4 motion-reduce:animate-none sm:p-5
           border-2 border-fino-line"
    role="status"
  >
    <span
      class="flex size-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/15 text-amber-700 dark:text-amber-400"
      aria-hidden="true"
    >
      <i class="pi pi-sync" />
    </span>

    <div class="min-w-0">
      <h2 class="text-sm font-semibold text-fino-text sm:text-base">
        {{ t('application.worldChange.title') }}
      </h2>

      <p class="mt-1 break-words text-sm leading-relaxed text-fino-text">
        {{ reason }}. {{ consequence }}
      </p>
    </div>
  </section>
</template>
