import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { ApplicationProductChoiceEnum } from '@/app/types/application/application-product-choice-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ApplicationFormInterface {
  product: Nullable<CreditProductCodeEnum | ApplicationProductChoiceEnum>
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
