import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { isNotFoundError } from '@/app/composables/useCashForecast'
import { applicationsService } from '@/app/services/application/applications.service'
import { companyProfileService } from '@/app/services/company/company-profile.service'
import { ApplicationsSummaryMapper } from '@/app/mappers/applications-summary.mapper'
import { CompanyProfileMapper } from '@/app/mappers/company-profile.mapper'
import type { AppLocale } from '@/app/i18n'
import type { ApplicationsSummaryInterface } from '@/app/types/application/applications-summary-interface'
import type { CompanyProfileInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Заявки и задачи, а также сведения банка о компании — по ИНН.
 * Состояния независимы: ошибка одного запроса не влияет на другой виджет.
 * Ошибки показываются локально в карточках, без всплывающих уведомлений.
 */
export function useCompanyOverview(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const applicationsSummary = ref<Nullable<ApplicationsSummaryInterface>>(null)
  const isApplicationsLoading = ref(false)
  const applicationsError = ref(false)

  const profile = ref<Nullable<CompanyProfileInterface>>(null)
  const isProfileLoading = ref(false)
  const profileError = ref(false)

  // Номера последних запросов: ответы по прежнему ИНН или языку отбрасываем
  let lastApplicationsRequestId = 0
  let lastProfileRequestId = 0

  async function loadApplicationsSummary() {
    const requestId = ++lastApplicationsRequestId

    isApplicationsLoading.value = true
    applicationsError.value = false

    try {
      const { data } = await applicationsService.fetchSummary(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastApplicationsRequestId) return

      applicationsSummary.value = ApplicationsSummaryMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastApplicationsRequestId) return

      console.error('Applications summary loading failed:', err)
      applicationsSummary.value = null
      applicationsError.value = !isNotFoundError(err)
    } finally {
      if (requestId === lastApplicationsRequestId) {
        isApplicationsLoading.value = false
      }
    }
  }

  async function loadProfile() {
    const requestId = ++lastProfileRequestId

    isProfileLoading.value = true
    profileError.value = false

    try {
      const { data } = await companyProfileService.fetchProfile(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastProfileRequestId) return

      profile.value = CompanyProfileMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastProfileRequestId) return

      console.error('Company profile loading failed:', err)
      profile.value = null
      profileError.value = !isNotFoundError(err)
    } finally {
      if (requestId === lastProfileRequestId) {
        isProfileLoading.value = false
      }
    }
  }

  function loadAll() {
    loadApplicationsSummary()
    loadProfile()
  }

  function onInnChange() {
    // Данные прежней компании убираем сразу, не дожидаясь ответа
    applicationsSummary.value = null
    profile.value = null
    loadAll()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadAll)

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
