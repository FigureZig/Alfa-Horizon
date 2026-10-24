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
  title: string
  text: string
  value: Nullable<number>
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
  // Сумма, которую банк готов дать: сработавший лимит с запасом и округлением
  limitAmount: Nullable<number>
  // Факторы оценки без данных — по ним видно, что решение пришло без кредитной истории
  missingFactors: string[]
  pathTitle: Nullable<string>
  pathBlocked: boolean
  pathOptions: ExplanationPathOptionInterface[]
}
