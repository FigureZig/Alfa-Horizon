import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RepaymentKindEnum } from '@/app/types/catalog/repayment-kind-enum'
import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

/**
 * Тело POST v1/calc/loan. Без `rate` бэкенд считает ставку сам: по продукту, отрасли (`section`),
 * классу риска и форме компании.
 */
export interface LoanCalcRequestDto {
  amount: number
  term_months: number
  rate?: number
  product: CreditProductCodeEnum
  section?: string
  risk_class: RiskClassEnum
  segment: LegalFormEnum
}

// Деньги и ставки приходят строками — число получает маппер
export interface LoanCalcRatePartsDto {
  total: string
  key_rate: string
  industry: string
  risk: string
  risk_class: RiskClassEnum
}

export interface LoanCalcScheduleRowDto {
  n: number
  payment: string
  interest: string
  principal: string
  balance: string
}

export interface LoanCalcDto {
  rate: string
  rate_parts: Nullable<LoanCalcRatePartsDto>
  repayment: RepaymentKindEnum
  payment: string
  overpayment: string
  schedule: LoanCalcScheduleRowDto[]
}
