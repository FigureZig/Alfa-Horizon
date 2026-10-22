import type { ApplicationReasonDto } from '@/app/types/application/application-dto'
import type { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ExplanationFactorNextDto {
  target: number | string
  gain: number
}

export interface ExplanationFactorDto {
  factor: string
  title: string
  value: unknown
  points: number
  effect: 'plus' | 'neutral' | 'minus' | 'unknown'
  text: Nullable<string>
  next: Nullable<ExplanationFactorNextDto>
}

export interface ExplanationScoringDto {
  score: Nullable<number>
  pd: Nullable<number>
  risk_class: Nullable<string>
  factors: ExplanationFactorDto[]
}

export interface ExplanationPricePartDto {
  part: string
  value: string
  text: string
}

export interface ExplanationPriceDto {
  total: string
  parts: ExplanationPricePartDto[]
}

export interface ExplanationCapDto {
  code: string
  text: string
}

export interface ExplanationLimitDto {
  caps: ExplanationCapDto[]
  binding: Nullable<string>
}

export interface ExplanationPathOptionDto {
  levers: string[]
  title: string
  outcome: DecisionOutcomeEnum
  risk_class: Nullable<string>
  amount: Nullable<string>
  rate: Nullable<string>
}

export interface ExplanationPathDto {
  changeable: boolean
  blocked_by: string[]
  options: ExplanationPathOptionDto[]
}

/** Ответ GET v1/applications/{id}/explain — «почему такое решение и как получить одобрение». */
export interface ApplicationExplanationDto {
  outcome: DecisionOutcomeEnum
  reasons: ApplicationReasonDto[]
  scoring: ExplanationScoringDto
  price: Nullable<ExplanationPriceDto>
  limit: Nullable<ExplanationLimitDto>
  path_to_approval: ExplanationPathDto
}
