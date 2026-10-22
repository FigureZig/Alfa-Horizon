import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { RepaymentKindEnum } from '@/app/types/catalog/repayment-kind-enum'

/** Карточка продукта витрины: GET v1/catalog/products. Суммы и ставки здесь — числа. */
export interface CatalogProductDto {
  id: CreditProductCodeEnum
  name: string
  benefits: string[]
  amount_min: number
  amount_max: number
  term_months_min: number
  term_months_max: number
  rate_from: number
  decision: 'auto' | 'specialist'
  decision_text: string
  repayment: RepaymentKindEnum
  goals: CreditGoalEnum[]
}

export interface CatalogKeyRateDto {
  value: number
  since: string
}

export interface CatalogProductsDto {
  key_rate: CatalogKeyRateDto
  products: CatalogProductDto[]
}
