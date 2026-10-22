import type { CreditScoreEffectEnum } from '@/app/types/company/credit-score-effect-enum'
import type { CreditScoreLeverWayEnum } from '@/app/types/company/credit-score-lever-way-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CreditScoreFactorInterface {
  factor: string
  title: string
  value: Nullable<number>
  points: number
  effect: CreditScoreEffectEnum
  text: Nullable<string>
}

export interface CreditScoreLeverInterface {
  factor: string
  title: string
  value: Nullable<number>
  target: number
  way: CreditScoreLeverWayEnum
  gain: number
}

export interface CreditScoreClassInterface {
  riskClass: RiskClassEnum
  min: number
}

export interface CreditScoreInterface {
  score: number
  riskClass: RiskClassEnum
  bestClass: RiskClassEnum
  bkiKnown: boolean
  // Факторы с неизвестным значением (например, нет кредитной истории): балл по ним пока не считается
  hasMissingFactors: boolean
  factors: CreditScoreFactorInterface[]
  levers: CreditScoreLeverInterface[]
  classes: CreditScoreClassInterface[]
}
