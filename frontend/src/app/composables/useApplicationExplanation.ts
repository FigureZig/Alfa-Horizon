import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationExplanationMapper } from '@/app/mappers/application-explanation.mapper'
import type { AppLocale } from '@/app/i18n'
import type { ApplicationExplanationInterface } from '@/app/types/application/application-explanation-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * «Почему такое решение»: скоринг, ставка из частей, лимит и путь к одобрению.
 * Грузится, когда у заявки есть решение (`version` меняется — решение пересчитано, грузим заново).
 */
export function useApplicationExplanation(
  applicationId: MaybeRefOrGetter<string>,
  version: MaybeRefOrGetter<Nullable<string>>,
) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const explanation = ref<Nullable<ApplicationExplanationInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  let lastRequestId = 0

  async function loadExplanation() {
    // Версия пуста, пока решения по заявке нет
    if (!toValue(version)) {
      explanation.value = null
      return
    }

    const requestId = ++lastRequestId

    isLoading.value = true
    error.value = false

    try {
      const { data } = await applicationsService.fetchExplanation(
        $fetch,
        toValue(applicationId),
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      explanation.value = ApplicationExplanationMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Application explanation loading failed:', err)
      explanation.value = null
      error.value = true
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  watch([() => toValue(applicationId), () => toValue(version), locale], loadExplanation, { immediate: true })

  return { explanation, isLoading, error, loadExplanation }
}
