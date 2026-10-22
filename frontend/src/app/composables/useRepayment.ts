import { onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import { useI18n } from 'vue-i18n'
import debounce from 'lodash-es/debounce'
import { isNotFoundError, useApiFetch } from '@/app/composables/useApiFetch'
import { companyRepaymentService } from '@/app/services/company/company-repayment.service'
import type { RepaymentParams } from '@/app/services/company/company-repayment.service'
import { RepaymentMapper } from '@/app/mappers/repayment.mapper'
import type { AppLocale } from '@/app/i18n'
import type { RepaymentInterface } from '@/app/types/company/repayment-interface'
import type { Nullable } from '@/app/types/nullable'

const REPAYMENT_DEBOUNCE = 350

/**
 * K4 — как гасить кредит: фиксированный график или доля поступлений, со стресс-тестом на худших месяцах.
 * `isUnavailable`: функция выключена на бэкенде или у ИНН нет графика погашения — блок не показываем.
 */
export function useRepayment(inn: MaybeRefOrGetter<string>, params: MaybeRefOrGetter<Nullable<RepaymentParams>>) {
  const $fetch = useApiFetch()
  const { locale } = useI18n({ useScope: 'global' })

  const repayment = ref<Nullable<RepaymentInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)
  const isUnavailable = ref(false)

  let lastRequestId = 0

  async function loadRepayment() {
    const current = toValue(params)
    const requestId = ++lastRequestId

    if (!current) {
      repayment.value = null
      isLoading.value = false

      return
    }

    isLoading.value = true
    error.value = false

    try {
      const { data } = await companyRepaymentService.fetchRepayment(
        $fetch,
        toValue(inn),
        current,
        locale.value as AppLocale,
      )

      if (requestId !== lastRequestId) return

      isUnavailable.value = false
      repayment.value = RepaymentMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Repayment loading failed:', err)
      repayment.value = null
      isUnavailable.value = isNotFoundError(err)
      error.value = !isUnavailable.value
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  const loadRepaymentDebounced = debounce(loadRepayment, REPAYMENT_DEBOUNCE)

  function onParamsChange() {
    if (toValue(params)) {
      isLoading.value = true
    }

    loadRepaymentDebounced()
  }

  watch([() => toValue(params), () => toValue(inn), locale], onParamsChange, { deep: true, immediate: true })
  onBeforeUnmount(loadRepaymentDebounced.cancel)

  return { repayment, isLoading, error, isUnavailable, loadRepayment }
}
