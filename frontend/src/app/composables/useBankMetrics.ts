import { onMounted, ref } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankMetricsMapper } from '@/app/mappers/bank-metrics.mapper'
import type { BankMetricsInterface } from '@/app/types/bank/bank-metrics-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Метрики конвейера решений для рабочего места банка.
 */
export function useBankMetrics() {
  const $fetch = useApiFetch()

  const metrics = ref<Nullable<BankMetricsInterface>>(null)
  const isMetricsLoading = ref(false)
  const metricsError = ref(false)

  async function loadMetrics() {
    if (isMetricsLoading.value) return

    isMetricsLoading.value = true
    metricsError.value = false

    try {
      const { data } = await bankService.fetchMetrics($fetch)

      metrics.value = BankMetricsMapper.toEntity(data.data)
    } catch (err: unknown) {
      console.error('Bank metrics loading failed:', err)
      metricsError.value = true
    } finally {
      isMetricsLoading.value = false
    }
  }

  onMounted(loadMetrics)

  return {
    metrics,
    isMetricsLoading,
    metricsError,
    loadMetrics,
  }
}
