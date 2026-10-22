import { ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { companyProfileService } from '@/app/services/company/company-profile.service'
import { CompanyProfileMapper } from '@/app/mappers/company-profile.mapper'
import type { AppLocale } from '@/app/i18n'
import type { CompanyProfileInterface } from '@/app/types/company/company-profile-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Что банк знает о компании по ИНН. Ошибка показывается локально в виджете, без всплывающих уведомлений.
 */
export function useCompanyProfile(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const profile = ref<Nullable<CompanyProfileInterface>>(null)
  const isProfileLoading = ref(false)
  const profileError = ref(false)

  // Номер последнего запроса: ответы по прежнему ИНН или языку отбрасываем
  let lastRequestId = 0

  async function loadProfile() {
    const requestId = ++lastRequestId

    isProfileLoading.value = true
    profileError.value = false

    try {
      const { data } = await companyProfileService.fetchProfile(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      profile.value = CompanyProfileMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Company profile loading failed:', err)
      profile.value = null
      profileError.value = !isNotFoundError(err)
    } finally {
      if (requestId === lastRequestId) {
        isProfileLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Данные прежней компании убираем сразу, не дожидаясь ответа
    profile.value = null
    loadProfile()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadProfile)

  return { profile, isProfileLoading, profileError, loadProfile }
}
