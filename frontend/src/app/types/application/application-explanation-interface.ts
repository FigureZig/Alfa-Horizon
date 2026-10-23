import type { ApplicationReasonInterface } from '@/app/types/application/application-interface'
import type { DecisionOutcomeEnum } from '@/app/types/application/decision-outcome-enum'
import type { Nullable } from '@/app/types/nullable'

export interface ExplanationFactorInterface {
  factor: string
  title: string
  points: number
  effect: 'plus' | 'neutral' | 'minus' | 'unknown'
  text: Nullable<string>
  gain: Nullable<number>
}

export interface ExplanationPricePartInterface {
  part: string
  value: number
  text: string
}

export interface ExplanationPathOptionInterface {
  title: string
  outcome: DecisionOutcomeEnum
  riskClass: Nullable<string>
  amount: Nullable<number>
  rate: Nullable<number>
}

export interface ExplanationCapInterface {
  code: string
  text: string
  // Сработавший лимит: выделяется в списке
  isBinding: boolean
}

export interface ApplicationExplanationInterface {
  outcome: DecisionOutcomeEnum
  reasons: ApplicationReasonInterface[]
  score: Nullable<number>
  riskClass: Nullable<string>
  factors: ExplanationFactorInterface[]
  rate: Nullable<number>
  priceParts: ExplanationPricePartInterface[]
  caps: ExplanationCapInterface[]
  pathTitle: Nullable<string>
  pathBlocked: boolean
  pathOptions: ExplanationPathOptionInterface[]
}
