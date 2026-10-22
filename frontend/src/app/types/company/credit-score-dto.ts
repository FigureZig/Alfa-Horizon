import type { CreditScoreEffectEnum } from '@/app/types/company/credit-score-effect-enum'
import type { CreditScoreLeverWayEnum } from '@/app/types/company/credit-score-lever-way-enum'
import type { RiskClassEnum } from '@/app/types/company/risk-class-enum'
import type { Nullable } from '@/app/types/nullable'

export interface CreditScoreContributionDto {
  factor: string
  title: string
  value: Nullable<number>
  points: number
  effect: CreditScoreEffectEnum
  text: Nullable<string>
}

export interface CreditScoreLeverDto {
  factor: string
  value: Nullable<number>
  target: number
  way: CreditScoreLeverWayEnum
  gain: number
}

export interface CreditScoreClassDto {
  class: RiskClassEnum
  min: number
}

/**
 * Ответ GET v1/companies/{inn}/score (K3) — кредитное здоровье до заявки:
 * балл, класс риска, вклад каждого фактора и рычаги — до какого значения подтянуть фактор и сколько баллов это даст.
 */
export interface CreditScoreDto {
  inn: string
  bki_known: boolean
  score: number
  pd: number
  class: RiskClassEnum
  best_class: RiskClassEnum
  contributions: CreditScoreContributionDto[]
  missing: string[]
  base: number
  classes: CreditScoreClassDto[]
  levers: CreditScoreLeverDto[]
}
