import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ApplicationFormInterface {
  product: Nullable<CreditProductCodeEnum>
  amount: Nullable<number>
  termMonths: Nullable<number>
  goal: Nullable<CreditGoalEnum>
  consentBki: boolean
}

export interface ApplicationInfoAnswerInterface {
  corporateApproval: boolean
  collateralValue: Nullable<number>
  documents: string[]
  comment: string
}
