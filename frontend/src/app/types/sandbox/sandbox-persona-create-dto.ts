import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'

/**
 * Тело POST v1/sandbox/personas для клиента с компанией. ИНН и тексты карточки
 * бэкенд генерирует из параметров компании.
 */
export interface SandboxPersonaCreateDto {
  full_name: string
  inn?: string
  organization?: string
  form: LegalFormEnum
  okved: string
  okved_name: string
  age_months: number
  headcount: number
  inflow_avg: number
  inflow_cv: number
  inflow_trend: number
  debt_load: number
  overdue_days: number
  bki_requests: number
  tax_debt: number
  participants: number
  profit_margin: number
  contract_price?: number
  flags: string[]
}
