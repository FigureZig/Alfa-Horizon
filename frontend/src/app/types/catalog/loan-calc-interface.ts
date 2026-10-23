import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RepaymentKindEnum } from '@/app/types/catalog/repayment-kind-enum'
import type { LegalFormEnum } from '@/app/types/company/legal-form-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

/** Данные компании, от которых зависит ставка: форма, раздел ОКВЭД и класс риска. */
export interface LoanCalcContextInterface {
  segment: LegalFormEnum
  section: Nullable<string>
  riskClass: RiskClassEnum
}

/** Что считаем: продукт, сумма и срок плюс данные компании. */
export interface LoanCalcParamsInterface extends LoanCalcContextInterface {
  product: CreditProductCodeEnum
  amount: number
  termMonths: number
}

export interface LoanCalcScheduleRowInterface {
  number: number
  payment: number
  interest: number
  principal: number
  balance: number
}

export interface LoanCalcUsageExampleInterface {
  amount: number
  days: number
  interest: number
  text: string
}

export interface LoanCalcInterface {
  rate: number
  keyRate: Nullable<number>
  industrySpread: Nullable<number>
  riskSpread: Nullable<number>
  riskClass: Nullable<RiskClassEnum>
  repayment: RepaymentKindEnum
  payment: number
  overpayment: Nullable<number>
  usageExample: Nullable<LoanCalcUsageExampleInterface>
  schedule: LoanCalcScheduleRowInterface[]
}
