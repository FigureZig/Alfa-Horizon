/**
 * Предодобренный кредитный продукт (результат K2) из GET v1/companies/{inn}/products.
 * `amount` — доступный лимит; `is_rate_from` — ставка «от»;
 * `is_preliminary` — предварительное решение по данным банка;
 * `is_recommended` — предложение подобрано под найденный кассовый разрыв.
 */
export interface CreditProductDto {
  id: string
  name: string
  amount: number
  currency: string
  rate: number
  is_rate_from: boolean
  term_months: number
  benefits: string[]
  is_preliminary: boolean
  is_recommended: boolean
}
