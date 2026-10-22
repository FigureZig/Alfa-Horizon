import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'

/** Тело POST v1/applications — черновик заявки. Подача — отдельной командой submit. */
export interface ApplicationCreateDto {
  inn: string
  product: CreditProductCodeEnum
  amount: number
  term_months?: number
  goal?: CreditGoalEnum
  consent_bki: boolean
}

/** Тело POST v1/applications/{id}/info-requests/answer: ответ на запрос банка. */
export interface ApplicationInfoAnswerDto {
  corporate_approval?: boolean
  collateral_value?: number
  documents?: string[]
  comment?: string
}
