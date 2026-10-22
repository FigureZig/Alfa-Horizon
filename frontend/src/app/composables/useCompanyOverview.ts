import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { useCompanyProfile } from '@/app/composables/useCompanyProfile'
import { applicationsService } from '@/app/services/application/applications.service'
import { ApplicationsSummaryMapper } from '@/app/mappers/applications-summary.mapper'
import type { AppLocale } from '@/app/i18n'
import type { ApplicationsSummaryInterface } from '@/app/types/application/applications-summary-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Заявки и задачи, а также сведения банка о компании — по ИНН.
 * Состояния независимы: ошибка одного запроса не влияет на другой виджет.
 * Ошибки показываются локально в карточках, без всплывающих уведомлений.
 */
export function useCompanyOverview(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const { profile, isProfileLoading, profileError, loadProfile } = useCompanyProfile(inn)

  const applicationsSummary = ref<Nullable<ApplicationsSummaryInterface>>(null)
  const isApplicationsLoading = ref(false)
  const applicationsError = ref(false)

  // Номер последнего запроса: ответы по прежнему ИНН или языку отбрасываем
  let lastRequestId = 0

  async function loadApplicationsSummary() {
    const requestId = ++lastRequestId

    isApplicationsLoading.value = true
    applicationsError.value = false

    try {
      const { data } = await applicationsService.fetchSummary(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      applicationsSummary.value = ApplicationsSummaryMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Applications summary loading failed:', err)
      applicationsSummary.value = null
      applicationsError.value = !isNotFoundError(err)
    } finally {
      if (requestId === lastRequestId) {
        isApplicationsLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Данные прежней компании убираем сразу, не дожидаясь ответа
    applicationsSummary.value = null
    loadApplicationsSummary()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadApplicationsSummary)

  return {
    applicationsSummary,
    isApplicationsLoading,
    applicationsError,
    loadApplicationsSummary,
    profile,
    isProfileLoading,
    profileError,
    loadProfile,
  }
}
