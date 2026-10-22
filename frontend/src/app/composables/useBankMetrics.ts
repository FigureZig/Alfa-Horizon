import { onMounted, ref } from 'vue'
import { useApiFetch } from '@/app/composables/useApiFetch'
import { bankService } from '@/app/services/bank/bank.service'
import { BankAuditMapper } from '@/app/mappers/bank-audit.mapper'
import { BankMetricsMapper } from '@/app/mappers/bank-metrics.mapper'
import type { BankAuditInterface } from '@/app/types/bank/bank-audit-interface'
import type { BankMetricsInterface } from '@/app/types/bank/bank-metrics-interface'
import type { Nullable } from '@/app/types/nullable'

/**
 * Метрики конвейера и проверка журнала аудита. Состояния независимы: сбой проверки журнала
 * не прячет метрики, и наоборот.
 */
export function useBankMetrics() {
  const $fetch = useApiFetch()

  const metrics = ref<Nullable<BankMetricsInterface>>(null)
  const isMetricsLoading = ref(false)
  const metricsError = ref(false)

  const audit = ref<Nullable<BankAuditInterface>>(null)
  const isAuditLoading = ref(false)
  const auditError = ref(false)

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

  async function loadAudit() {
    if (isAuditLoading.value) return

    isAuditLoading.value = true
    auditError.value = false

    try {
      const { data } = await bankService.fetchAudit($fetch)

      audit.value = BankAuditMapper.toEntity(data.data)
    } catch (err: unknown) {
      console.error('Bank audit loading failed:', err)
      auditError.value = true
    } finally {
      isAuditLoading.value = false
    }
  }

  function loadAll() {
    loadMetrics()
    loadAudit()
  }

  onMounted(loadAll)

  return {
    metrics,
    isMetricsLoading,
    metricsError,
    loadMetrics,
    audit,
    isAuditLoading,
    auditError,
    loadAudit,
    loadAll,
  }
}
