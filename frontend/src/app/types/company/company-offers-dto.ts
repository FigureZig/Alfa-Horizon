import type { CreditGoalEnum } from '@/app/types/application/credit-goal-enum'
import type { CreditProductCodeEnum } from '@/app/types/application/credit-product-code-enum'
import type { Nullable } from '@/app/types/nullable'

// Что мешает банку предложить кредит всей компании: недоимка, банкротство, недостоверный директор, лимит нагрузки…
export interface CompanyBlockerDto {
  code: string
  text: string
}

// Деньги в подборе приходят строками («1500000.00»): число получает маппер
export interface CompanyOfferTermsDto {
  amount: string
  term_months: number
  rate: string
  payment: string
  repayment: string
}

export interface CompanyOfferOptionDto {
  product: CreditProductCodeEnum
  name: string
  repayment: string
  available: boolean
  // PREAPPROVED · CONDITIONAL · REVIEW · UNAVAILABLE
  label: string
  max_amount: Nullable<string>
  offer: Nullable<CompanyOfferTermsDto>
  // Что понадобится, чтобы получить продукт: поручитель, залог, документы, согласие на запрос кредитной истории
  needs: Array<string | { code?: string; text: string }>
  // Почему продукт не подходит компании
  why: string[]
  recommended: boolean
}

/**
 * Ответ GET v1/companies/{inn}/offers: все продукты компании с личными условиями.
 * Без цели — общий подбор; с целью, суммой и сроком условия считаются под них.
 */
export interface CompanyOffersDto {
  inn: string
  goal: Nullable<CreditGoalEnum>
  amount: Nullable<number>
  term_months: Nullable<number>
  blockers: CompanyBlockerDto[]
  options: CompanyOfferOptionDto[]
  recommended: Nullable<CreditProductCodeEnum>
  // false — банк ещё не видел кредитную историю: суммы и ставки предварительные
  bki_known?: boolean
}
