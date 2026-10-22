import type { RepaymentRecommendationEnum } from '@/app/types/company/repayment-recommendation-enum'

export interface RepaymentFixedDto {
  payment: number
  total_interest: number
  worst3_inflow_avg: number
  worst3_share: number
  comfortable: boolean
}

export interface RepaymentFromInflowsDto {
  share: number
  min_payment: number
  months: number
  total_interest: number
  max_payment: number
  min_paid: number
}

/**
 * Ответ GET v1/companies/{inn}/repayment (K4): на истории счёта за 12 месяцев сравниваются фиксированный
 * аннуитет и погашение долей поступлений; стресс-тест — платёж к поступлениям трёх худших месяцев.
 * Здесь суммы — числа, как у остальной витрины кабинета.
 */
export interface RepaymentDto {
  inn: string
  amount: number
  rate: number
  term_months: number
  fixed: RepaymentFixedDto
  from_inflows: RepaymentFromInflowsDto
  recommendation: RepaymentRecommendationEnum
  why: string
  stress_max: number
}
