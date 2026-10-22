import { onBeforeUnmount, ref, toValue, watch } from 'vue'
import type { MaybeRefOrGetter } from 'vue'
import debounce from 'lodash-es/debounce'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { catalogService } from '@/app/services/catalog/catalog.service'
import { LoanCalcMapper } from '@/app/mappers/loan-calc.mapper'
import type { LoanCalcInterface, LoanCalcParamsInterface } from '@/app/types/catalog/loan-calc-interface'
import type { Nullable } from '@/app/types/nullable'

// Пересчитываем, когда пользователь закончил вводить сумму или срок
const CALC_DEBOUNCE = 350

/**
 * Калькулятор кредита на бэкенде: ставка по продукту, отрасли и классу риска, платёж, переплата и график.
 * `params === null` — расчёт невозможен (форма не заполнена или значения вне границ продукта).
 */
export function useLoanCalculator(params: MaybeRefOrGetter<Nullable<LoanCalcParamsInterface>>) {
  const $fetch = useApiFetch()

  const result = ref<Nullable<LoanCalcInterface>>(null)
  const isLoading = ref(false)
  const error = ref(false)

  let lastRequestId = 0

  async function calculate() {
    const current = toValue(params)
    const requestId = ++lastRequestId

    if (!current) {
      result.value = null
      isLoading.value = false
      error.value = false

      return
    }

    isLoading.value = true
    error.value = false

    try {
      const { data } = await catalogService.calculateLoan($fetch, LoanCalcMapper.toPayload(current))

      if (requestId !== lastRequestId) return

      result.value = LoanCalcMapper.toEntity(data.data)
    } catch (err: unknown) {
      if (requestId !== lastRequestId) return

      console.error('Loan calculation failed:', err)
      result.value = null
      error.value = true
    } finally {
      if (requestId === lastRequestId) {
        isLoading.value = false
      }
    }
  }

  const calculateDebounced = debounce(calculate, CALC_DEBOUNCE)

  function onParamsChange() {
    // Старый результат устарел: показываем загрузку, пока не пришёл новый
    if (toValue(params)) {
      isLoading.value = true
    }

    calculateDebounced()
  }

  watch(() => toValue(params), onParamsChange, { deep: true, immediate: true })
  onBeforeUnmount(calculateDebounced.cancel)

  return { result, isLoading, error, calculate }
}
