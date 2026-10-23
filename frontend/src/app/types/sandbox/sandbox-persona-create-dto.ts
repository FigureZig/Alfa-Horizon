import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'

/**
 * Тело POST v1/sandbox/personas, PUT v1/sandbox/personas/{id} и POST v1/sandbox/personas/preview.
 * Простые ответы (отрасль, устройство, кредиты…) бэкенд сам превращает в параметры компании;
 * точные цифры необязательны и важнее ответов.
 */
export interface SandboxPersonaCreateDto {
  kind: 'client'
  full_name?: string
  organization?: string
  inn?: string
  form: LegalFormEnum
  industry?: string
  structure?: string
  accountant: boolean
  representative: boolean
  seasonality?: string
  stability?: string
  trend?: string
  channel?: string
  loans?: string
  delays?: string
  age_months: number
  headcount: number
  inflow_avg: number
  okved?: string
  okved_name?: string
  inflow_cv?: number
  inflow_trend?: number
  debt_load?: number
  overdue_days?: number
  bki_requests?: number
  tax_debt?: number
  participants?: number
  profit_margin?: number
  contract_price?: number
  flags: string[]
}
