import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RepaymentKindEnum } from '@/app/types/catalog/repayment-kind-enum'

export interface CatalogProductInterface {
  code: CreditProductCodeEnum
  name: string
  benefits: string[]
  amountMin: number
  amountMax: number
  termMonthsMin: number
  termMonthsMax: number
  rateFrom: number
  decisionText: string
  repayment: RepaymentKindEnum
  goals: CreditGoalEnum[]
}
