import type { AxiosInstance } from 'axios'
import type { ApiResponse } from '@/app/types/api-response'
import type { ApplicationDto } from '@/app/types/application/application-dto'
import type { BankAuditDto } from '@/app/types/bank/bank-audit-dto'
import type { BankConfirmDto, BankDecisionDto } from '@/app/types/bank/bank-decision-dto'
import type { BankDossierDto } from '@/app/types/bank/bank-dossier-dto'
import type { BankMetricsDto } from '@/app/types/bank/bank-metrics-dto'
import type { BankQueueItemDto } from '@/app/types/bank/bank-queue-item-dto'

const ROUTE_PREFIX_BANK = 'v1/bank'

function applicationRoute(applicationId: string): string {
  return `${ROUTE_PREFIX_BANK}/applications/${encodeURIComponent(applicationId)}`
}

export const bankService = {
  // Очередь исключений: заявки, которые движок не смог решить сам
  async fetchQueue($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<BankQueueItemDto[]>>(`${ROUTE_PREFIX_BANK}/queue`)
  },

  async fetchMetrics($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<BankMetricsDto>>(`${ROUTE_PREFIX_BANK}/metrics`)
  },

  // Пересчитывает цепочку хэшей журнала аудита с первой записи
  async fetchAudit($fetch: AxiosInstance) {
    return await $fetch.get<ApiResponse<BankAuditDto>>(`${ROUTE_PREFIX_BANK}/audit`)
  },

  async fetchDossier($fetch: AxiosInstance, applicationId: string) {
    return await $fetch.get<ApiResponse<BankDossierDto>>(`${applicationRoute(applicationId)}/dossier`)
  },

  async decide($fetch: AxiosInstance, applicationId: string, payload: BankDecisionDto) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(`${applicationRoute(applicationId)}/decision`, payload)
  },

  // Второй ключ: подтверждает или возвращает одобрение специалиста выше его полномочий
  async confirm($fetch: AxiosInstance, applicationId: string, payload: BankConfirmDto) {
    return await $fetch.post<ApiResponse<ApplicationDto>>(`${applicationRoute(applicationId)}/decision/confirm`, payload)
  },
}
