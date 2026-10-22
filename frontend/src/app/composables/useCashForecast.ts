import { computed, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from 'primevue/usetoast'
import { getApiErrorCode, isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { companyInsightsService } from '@/app/services/company/company-insights.service'
import { CompanyInsightsMapper } from '@/app/mappers/company-insights.mapper'
import { CashForecastStatusEnum } from '@/app/types/company/cash-forecast-status-enum'
import { ApiErrorCodeEnum } from '@/app/types/api-error-code-enum'
import type { AppLocale } from '@/app/i18n'
import type { CashForecastInterface } from '@/app/types/company/cash-forecast-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * K1 — прогноз остатка по ИНН компании. Расчёт целиком на бэкенде.
 */
export function useCashForecast(inn: MaybeRefOrGetter<string>) {
  const $fetch = useApiFetch()
  const toast = useToast()
  const { t, locale } = useI18n({ useScope: 'global' })

  const forecast = ref<Nullable<CashForecastInterface>>(null)
  const isForecastLoading = ref(false)
  const forecastError = ref(false)
  // На бэкенде K1 выключен флагом (FEATURE_OFF) — блок прогноза не показываем
  const isForecastDisabled = ref(false)

  // Номер последнего запроса: ответы по прежнему ИНН или языку отбрасываем
  let lastRequestId = 0

  const hasCashGap = computed(() => forecast.value?.status === CashForecastStatusEnum.CashGap)

  async function loadForecast() {
    const requestId = ++lastRequestId

    isForecastLoading.value = true
    forecastError.value = false
    isForecastDisabled.value = false

    try {
      const { data } = await companyInsightsService.fetchInsights(
        $fetch,
        toValue(inn),
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      forecast.value = CompanyInsightsMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Cash forecast loading failed:', err)
      forecast.value = null

      if (getApiErrorCode(err) === ApiErrorCodeEnum.FeatureOff) {
        isForecastDisabled.value = true
        return
      }

      // 404 по ИНН показывает загрузка профиля персоны — здесь не дублируем уведомление
      if (isNotFoundError(err)) return

      forecastError.value = true

      toast.add({
        severity: 'error',
        summary: t('toast.error'),
        detail: t('toast.cashForecastLoadError'),
        life: 4000,
      })
    } finally {
      if (requestId === lastRequestId) {
        isForecastLoading.value = false
      }
    }
  }

  function onInnChange() {
    // Прогноз прежней компании убираем сразу, не дожидаясь ответа
    forecast.value = null
    loadForecast()
  }

  watch(() => toValue(inn), onInnChange, { immediate: true })
  watch(locale, loadForecast)

  return {
    forecast,
    isForecastLoading,
    forecastError,
    isForecastDisabled,
    hasCashGap,
    loadForecast,
  }
}
