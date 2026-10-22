export interface CreditProductInterface {
  id: string
  name: string
  amount: number
  currency: string
  rate: number
  isRateFrom: boolean
  termMonths: number
  benefits: string[]
  isPreliminary: boolean
  isRecommended: boolean
}
